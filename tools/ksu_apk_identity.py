#!/usr/bin/env python3
import hashlib
import os
import struct
import sys
import zipfile


NO_INDEX = 0xFFFFFFFF


class ApkIdentityError(Exception):
    pass


def usage():
    print(f"usage: {sys.argv[0]} <manager.apk> [package.name]", file=sys.stderr)
    raise SystemExit(2)


def fail(message):
    raise ApkIdentityError(message)


def read_u32(buf, offset):
    return struct.unpack_from("<I", buf, offset)[0]


def read_u64(buf, offset):
    return struct.unpack_from("<Q", buf, offset)[0]


def read_u16(buf, offset):
    return struct.unpack_from("<H", buf, offset)[0]


def decode_string_pool(buf, offset):
    string_count = read_u32(buf, offset + 8)
    flags = read_u32(buf, offset + 16)
    strings_start = read_u32(buf, offset + 20)
    utf8 = bool(flags & 0x00000100)

    offsets_base = offset + 28
    strings_base = offset + strings_start
    strings = []

    for i in range(string_count):
        string_offset = read_u32(buf, offsets_base + i * 4)
        pos = strings_base + string_offset

        if utf8:
            strlen, pos = read_length8(buf, pos)
            byte_len, pos = read_length8(buf, pos)
            raw = buf[pos:pos + byte_len]
            strings.append(raw.decode("utf-8", "replace"))
        else:
            strlen, pos = read_length16(buf, pos)
            raw = buf[pos:pos + strlen * 2]
            strings.append(raw.decode("utf-16le", "replace"))

    return strings


def read_length8(buf, offset):
    first = buf[offset]
    if first & 0x80:
        second = buf[offset + 1]
        return ((first & 0x7f) << 8) | second, offset + 2
    return first, offset + 1


def read_length16(buf, offset):
    first = read_u16(buf, offset)
    if first & 0x8000:
        second = read_u16(buf, offset + 2)
        return ((first & 0x7fff) << 16) | second, offset + 4
    return first, offset + 2


def string_at(strings, index, what):
    if index == NO_INDEX or index >= len(strings):
        fail(f"{what} string index out of range: {index}")
    return strings[index]


def extract_package_name(apk_path):
    with zipfile.ZipFile(apk_path, "r") as apk:
        try:
            manifest = apk.read("AndroidManifest.xml")
        except KeyError:
            fail("AndroidManifest.xml not found in APK")

    if read_u16(manifest, 0) != 0x0003:
        fail("AndroidManifest.xml is not binary XML")

    pos = read_u16(manifest, 2)
    strings = None

    while pos + 8 <= len(manifest):
        chunk_type = read_u16(manifest, pos)
        header_size = read_u16(manifest, pos + 2)
        chunk_size = read_u32(manifest, pos + 4)

        if chunk_size < header_size or chunk_size == 0:
            fail("invalid manifest chunk size")

        if chunk_type == 0x0001:
            strings = decode_string_pool(manifest, pos)
        elif chunk_type == 0x0102:
            if strings is None:
                fail("manifest string pool not found")

            ext_base = pos + header_size
            if ext_base + 20 > pos + chunk_size:
                fail("manifest start element chunk is truncated")

            name_idx = read_u32(manifest, ext_base + 4)
            attr_start = read_u16(manifest, ext_base + 8)
            attr_size = read_u16(manifest, ext_base + 10)
            attr_count = read_u16(manifest, ext_base + 12)

            if string_at(strings, name_idx, "element name") != "manifest":
                pos += chunk_size
                continue

            attrs_base = ext_base + attr_start
            attrs_end = attrs_base + attr_count * attr_size
            if attr_size < 12 or attrs_base < ext_base or attrs_end > pos + chunk_size:
                fail("manifest attribute table is invalid")

            for i in range(attr_count):
                attr = attrs_base + i * attr_size
                attr_name_idx = read_u32(manifest, attr + 4)
                raw_value_idx = read_u32(manifest, attr + 8)

                if string_at(strings, attr_name_idx, "attribute name") == "package":
                    if raw_value_idx == NO_INDEX:
                        fail("manifest package is not a raw string")
                    return string_at(strings, raw_value_idx, "package value")

        pos += chunk_size

    fail("manifest package name not found")


def main():
    if len(sys.argv) not in (2, 3):
        usage()

    apk_path = sys.argv[1]
    package = sys.argv[2] if len(sys.argv) == 3 else extract_package_name(apk_path)

    with open(apk_path, "rb") as fp:
        data = fp.read()

    eocd_start = max(0, len(data) - 0x10000 - 22)
    eocd = data.rfind(b"PK\x05\x06", eocd_start)
    if eocd < 0:
        fail("EOCD not found")

    cd_offset = read_u32(data, eocd + 16)
    footer = cd_offset - 24
    if footer < 0:
        fail("APK signing block footer is invalid")

    block_size = read_u64(data, footer)
    magic = data[footer + 8:footer + 24]
    if magic != b"APK Sig Block 42":
        fail("APK signing block not found")

    p = cd_offset - block_size
    end = footer

    while p < end:
        pair_size = read_u64(data, p)
        pair_id = read_u32(data, p + 8)
        value = data[p + 12:p + 8 + pair_size]

        if pair_id == 0x7109871A:
            q = 0
            q += 4  # signer sequence length
            q += 4  # signer length

            q += 4  # signed data length
            digests_size = read_u32(value, q)
            q += 4 + digests_size

            q += 4  # certificates length
            cert_size = read_u32(value, q)
            q += 4

            cert = value[q:q + cert_size]
            if len(cert) != cert_size:
                fail("certificate data is truncated")

            cert_hash = hashlib.sha256(cert).hexdigest()
            print("{")
            print(f'\t.package = "{package}",')
            print(f"\t.cert_size = 0x{cert_size:x},")
            print(f'\t.cert_sha256 = "{cert_hash}",')
            print("},")
            return

        p += 8 + pair_size

    fail("APK v2 signature block not found")


def run():
    try:
        main()
    except ApkIdentityError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
        raise SystemExit(1)
    except PermissionError as e:
        print(f"error: permission denied: {e.filename}", file=sys.stderr)
        raise SystemExit(1)
    except IsADirectoryError as e:
        print(f"error: path is a directory: {e.filename}", file=sys.stderr)
        raise SystemExit(1)
    except zipfile.BadZipFile:
        print("error: input is not a valid APK/zip file", file=sys.stderr)
        raise SystemExit(1)
    except (IndexError, struct.error, UnicodeDecodeError):
        print("error: APK metadata is malformed or truncated", file=sys.stderr)
        raise SystemExit(1)
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            os._exit(1)


if __name__ == "__main__":
    run()
