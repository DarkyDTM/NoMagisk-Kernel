#!/usr/bin/env python3
import hashlib
import struct
import sys
import zipfile


def usage():
    print(f"usage: {sys.argv[0]} <manager.apk> [package.name]", file=sys.stderr)
    raise SystemExit(2)


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


def extract_package_name(apk_path):
    with zipfile.ZipFile(apk_path, "r") as apk:
        manifest = apk.read("AndroidManifest.xml")

    if read_u16(manifest, 0) != 0x0003:
        raise SystemExit("AndroidManifest.xml is not binary XML")

    pos = read_u16(manifest, 2)
    strings = None

    while pos + 8 <= len(manifest):
        chunk_type = read_u16(manifest, pos)
        header_size = read_u16(manifest, pos + 2)
        chunk_size = read_u32(manifest, pos + 4)

        if chunk_type == 0x0001:
            strings = decode_string_pool(manifest, pos)
        elif chunk_type == 0x0102:
            if strings is None:
                raise SystemExit("manifest string pool not found")

            name_idx = read_u32(manifest, pos + 20)
            attr_start = read_u16(manifest, pos + 24)
            attr_size = read_u16(manifest, pos + 26)
            attr_count = read_u16(manifest, pos + 28)

            if strings[name_idx] != "manifest":
                pos += chunk_size
                continue

            attrs_base = pos + attr_start
            for i in range(attr_count):
                attr = attrs_base + i * attr_size
                attr_name_idx = read_u32(manifest, attr + 4)
                raw_value_idx = read_u32(manifest, attr + 8)

                if strings[attr_name_idx] == "package":
                    if raw_value_idx == 0xFFFFFFFF:
                        raise SystemExit("manifest package is not a raw string")
                    return strings[raw_value_idx]

        if chunk_size < header_size or chunk_size == 0:
            raise SystemExit("invalid manifest chunk size")
        pos += chunk_size

    raise SystemExit("manifest package name not found")


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
        raise SystemExit("EOCD not found")

    cd_offset = read_u32(data, eocd + 16)
    footer = cd_offset - 24
    if footer < 0:
        raise SystemExit("APK signing block footer is invalid")

    block_size = read_u64(data, footer)
    magic = data[footer + 8:footer + 24]
    if magic != b"APK Sig Block 42":
        raise SystemExit("APK signing block not found")

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
                raise SystemExit("certificate data is truncated")

            cert_hash = hashlib.sha256(cert).hexdigest()
            print("{")
            print(f'\t.package = "{package}",')
            print(f"\t.cert_size = 0x{cert_size:x},")
            print(f'\t.cert_sha256 = "{cert_hash}",')
            print("},")
            return

        p += 8 + pair_size

    raise SystemExit("APK v2 signature block not found")


if __name__ == "__main__":
    main()
