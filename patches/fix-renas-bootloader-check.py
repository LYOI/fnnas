#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix-renas-bootloader-check.py

为 fnnas 的 renas 增加 rockchip 引导器写入校验。

背景
----
renas 的 make_image() 中，rockchip 平台写引导器的四个 if/elif 分支都以
${uboot_path}/rockchip/${board}/${BOOTLOADER_IMG} 文件存在为前提，且 dd 后面
接了 2>/dev/null。文件缺失时分支不成立、dd 不执行、错误也没有任何输出，
脚本继续执行，最终产出 0-16MB 全为零的镜像，用户线刷后开机全黑
（RK3399 BootROM 阶段 UART 静默，串口也无输出）。

本补丁在 rockchip 写入逻辑之后加一道签名校验，不通过则 error_msg 中止，
避免坏镜像发到用户手里。

用法
----
    python3 fix-renas-bootloader-check.py <fnnas 仓库根目录>
例如
    python3 fix-renas-bootloader-check.py .

幂等：重复执行不会重复插入。
"""

import os
import sys

MARKER = "    # Write bootloader for Allwinner platform"

BLOCK = '''    # Verify that the bootloader has really been written into the image.
    # A missing [ ${bootloader_path}/${BOOTLOADER_IMG} ] used to be swallowed by
    # [ 2>/dev/null ] and produced a non-bootable image without any warning.
    [[ "${PLATFORM}" == "rockchip" ]] && {
        if [[ "$(dd if="${loop_new}" bs=1 skip=34816 count=4 2>/dev/null)" != "RK33" ]]; then
            error_msg "Bootloader signature is missing at the 0x8800 offset of [ ${build_image_file} ], check [ ${bootloader_path}/${BOOTLOADER_IMG} ]."
        fi
    }

'''

CHECK = "Bootloader signature is missing at the 0x8800"


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    path = os.path.join(root, "renas")
    if not os.path.isfile(path):
        sys.exit("not found: %s" % path)

    with open(path, encoding="utf-8") as f:
        src = f.read()

    if CHECK in src:
        print("already patched, nothing to do")
        return 0

    n = src.count(MARKER)
    if n != 1:
        sys.exit("marker count = %d, abort" % n)

    src = src.replace(MARKER, BLOCK + MARKER, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)

    print("patched: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
