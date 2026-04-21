#!/usr/bin/env python3
"""
ReSukiSU Manual Hooks — автоматическое применение для ядра 5.4 arm64
Запуск из корня исходников ядра: python3 apply_ksu_hooks.py
"""

import sys
import os
from pathlib import Path

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"

def log_ok(msg):  print(f"{GREEN}[OK]{RESET} {msg}")
def log_err(msg): print(f"{RED}[ERR]{RESET} {msg}"); sys.exit(1)
def log_info(msg):print(f"{YELLOW}[..]{RESET} {msg}")

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def patch(path, old, new, description):
    log_info(f"{path}: {description}")
    content = read(path)
    if new.strip() in content:
        log_ok(f"уже применено — пропускаем ({description})")
        return
    if old not in content:
        log_err(f"не найден якорь в {path}!\nИщем:\n{old}\n\nВозможно структура файла отличается.")
    write(path, content.replace(old, new, 1))
    log_ok(description)

# ─────────────────────────────────────────────
# Проверка что запущено из корня исходников
# ─────────────────────────────────────────────
for check in ["fs/stat.c", "fs/exec.c", "fs/open.c", "kernel/reboot.c"]:
    if not Path(check).exists():
        log_err(f"Файл {check} не найден. Запусти скрипт из корня исходников ядра.")

# ═══════════════════════════════════════════════════════════
# 1. fs/stat.c
# ═══════════════════════════════════════════════════════════

# 1a. Объявления extern — вставить перед #if !defined(__ARCH_WANT_STAT64)
patch(
    "fs/stat.c",
    "#if !defined(__ARCH_WANT_STAT64) || defined(__ARCH_WANT_SYS_NEWFSTATAT)\n"
    "SYSCALL_DEFINE4(newfstatat,",
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "__attribute__((hot))\n"
    "extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);\n"
    "extern void ksu_handle_newfstat_ret(unsigned int *fd, struct stat __user **statbuf_ptr);\n"
    "#if defined(__ARCH_WANT_STAT64) || defined(__ARCH_WANT_COMPAT_STAT64)\n"
    "extern void ksu_handle_fstat64_ret(unsigned long *fd, struct stat64 __user **statbuf_ptr);\n"
    "#endif\n"
    "#endif\n"
    "\n"
    "#if !defined(__ARCH_WANT_STAT64) || defined(__ARCH_WANT_SYS_NEWFSTATAT)\n"
    "SYSCALL_DEFINE4(newfstatat,",
    "stat.c: добавить extern-объявления"
)

# 1b. Хук в newfstatat — перед vfs_fstatat
patch(
    "fs/stat.c",
    "SYSCALL_DEFINE4(newfstatat, int, dfd, const char __user *, filename,\n"
    "\t\tstruct stat __user *, statbuf, int, flag)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error;\n"
    "\terror = vfs_fstatat(",
    "SYSCALL_DEFINE4(newfstatat, int, dfd, const char __user *, filename,\n"
    "\t\tstruct stat __user *, statbuf, int, flag)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error;\n"
    "\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_stat(&dfd, &filename, &flag);\n"
    "#endif\n"
    "\terror = vfs_fstatat(",
    "stat.c: хук в newfstatat"
)

# 1c. Хук возврата в newfstat
patch(
    "fs/stat.c",
    "SYSCALL_DEFINE2(newfstat, unsigned int, fd, struct stat __user *, statbuf)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error = vfs_fstat(fd, &stat);\n"
    "\tif (!error)\n"
    "\t\terror = cp_new_stat(&stat, statbuf);\n"
    "\treturn error;\n"
    "}",
    "SYSCALL_DEFINE2(newfstat, unsigned int, fd, struct stat __user *, statbuf)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error = vfs_fstat(fd, &stat);\n"
    "\tif (!error)\n"
    "\t\terror = cp_new_stat(&stat, statbuf);\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_newfstat_ret(&fd, &statbuf);\n"
    "#endif\n"
    "\treturn error;\n"
    "}",
    "stat.c: хук возврата в newfstat"
)

# 1d. Хук возврата в fstat64
patch(
    "fs/stat.c",
    "SYSCALL_DEFINE2(fstat64, unsigned long, fd, struct stat64 __user *, statbuf)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error = vfs_fstat(fd, &stat);\n"
    "\tif (!error)\n"
    "\t\terror = cp_new_stat64(&stat, statbuf);\n"
    "\treturn error;\n"
    "}",
    "SYSCALL_DEFINE2(fstat64, unsigned long, fd, struct stat64 __user *, statbuf)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error = vfs_fstat(fd, &stat);\n"
    "\tif (!error)\n"
    "\t\terror = cp_new_stat64(&stat, statbuf);\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_fstat64_ret(&fd, &statbuf);\n"
    "#endif\n"
    "\treturn error;\n"
    "}",
    "stat.c: хук возврата в fstat64"
)

# 1e. Хук в fstatat64 — перед vfs_fstatat
patch(
    "fs/stat.c",
    "SYSCALL_DEFINE4(fstatat64, int, dfd, const char __user *, filename,\n"
    "\t\tstruct stat64 __user *, statbuf, int, flag)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error;\n"
    "\terror = vfs_fstatat(",
    "SYSCALL_DEFINE4(fstatat64, int, dfd, const char __user *, filename,\n"
    "\t\tstruct stat64 __user *, statbuf, int, flag)\n"
    "{\n"
    "\tstruct kstat stat;\n"
    "\tint error;\n"
    "\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_stat(&dfd, &filename, &flag);\n"
    "#endif\n"
    "\terror = vfs_fstatat(",
    "stat.c: хук в fstatat64"
)

# ═══════════════════════════════════════════════════════════
# 2. fs/exec.c
# ═══════════════════════════════════════════════════════════

# 2a. extern-объявление + хук в do_execve
patch(
    "fs/exec.c",
    "int do_execve(struct filename *filename,\n"
    "\tconst char __user *const __user *__argv,\n"
    "\tconst char __user *const __user *__envp)\n"
    "{\n"
    "\tstruct user_arg_ptr argv = { .ptr.native = __argv };\n"
    "\tstruct user_arg_ptr envp = { .ptr.native = __envp };\n"
    "\treturn do_execveat_common(AT_FDCWD, filename, argv, envp, 0);\n"
    "}",
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "__attribute__((hot))\n"
    "extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,\n"
    "\t\t\t\tvoid *argv, void *envp, int *flags);\n"
    "#endif\n"
    "\n"
    "int do_execve(struct filename *filename,\n"
    "\tconst char __user *const __user *__argv,\n"
    "\tconst char __user *const __user *__envp)\n"
    "{\n"
    "\tstruct user_arg_ptr argv = { .ptr.native = __argv };\n"
    "\tstruct user_arg_ptr envp = { .ptr.native = __envp };\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_execveat((int *)AT_FDCWD, &filename, &argv, &envp, 0);\n"
    "#endif\n"
    "\treturn do_execveat_common(AT_FDCWD, filename, argv, envp, 0);\n"
    "}",
    "exec.c: extern + хук в do_execve"
)

# 2b. Хук в compat_do_execve
patch(
    "fs/exec.c",
    "\t.ptr.compat = __envp,\n"
    "\t};\n"
    "\treturn do_execveat_common(AT_FDCWD, filename, argv, envp, 0);\n"
    "}\n"
    "\n"
    "static int compat_do_execveat(",
    "\t.ptr.compat = __envp,\n"
    "\t};\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_execveat((int *)AT_FDCWD, &filename, &argv, &envp, 0);\n"
    "#endif\n"
    "\treturn do_execveat_common(AT_FDCWD, filename, argv, envp, 0);\n"
    "}\n"
    "\n"
    "static int compat_do_execveat(",
    "exec.c: хук в compat_do_execve"
)

# ═══════════════════════════════════════════════════════════
# 3. fs/open.c
# ═══════════════════════════════════════════════════════════

patch(
    "fs/open.c",
    "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)\n"
    "{\n"
    "\treturn do_faccessat(dfd, filename, mode);\n"
    "}",
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "__attribute__((hot))\n"
    "extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n"
    "\t\t\t\tint *mode, int *flags);\n"
    "#endif\n"
    "\n"
    "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)\n"
    "{\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);\n"
    "#endif\n"
    "\treturn do_faccessat(dfd, filename, mode);\n"
    "}",
    "open.c: extern + хук в faccessat"
)

# ═══════════════════════════════════════════════════════════
# 4. kernel/reboot.c
# ═══════════════════════════════════════════════════════════

patch(
    "kernel/reboot.c",
    "SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,\n"
    "\t\tvoid __user *, arg)\n"
    "{\n"
    "\tstruct pid_namespace *pid_ns = task_active_pid_ns(current);\n"
    "\tchar buffer[256];\n"
    "\tint ret = 0;\n"
    "\t/* We only trust the superuser with rebooting the system. */",
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg);\n"
    "#endif\n"
    "\n"
    "SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,\n"
    "\t\tvoid __user *, arg)\n"
    "{\n"
    "\tstruct pid_namespace *pid_ns = task_active_pid_ns(current);\n"
    "\tchar buffer[256];\n"
    "\tint ret = 0;\n"
    "\n"
    "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
    "\tksu_handle_sys_reboot(magic1, magic2, cmd, &arg);\n"
    "#endif\n"
    "\t/* We only trust the superuser with rebooting the system. */",
    "reboot.c: extern + хук в reboot syscall"
)

# ═══════════════════════════════════════════════════════════
print(f"\n{GREEN}Все хуки успешно применены!{RESET}")
print("Теперь убедись что в конфиге ядра включено:")
print("  CONFIG_KSU=y")
print("  CONFIG_KSU_MANUAL_HOOK=y")
print("  CONFIG_KSU_MANUAL_HOOK_AUTO_INPUT_HOOK=y   (если нет ручного input хука)")
print("  CONFIG_KSU_MANUAL_HOOK_AUTO_SETUID_HOOK=y  (для 5.4 обязательно)")
print("  CONFIG_KSU_MANUAL_HOOK_AUTO_INITRC_HOOK=y  (для 5.4 обязательно)")
