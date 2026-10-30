# RK3399 引导器缺失问题（SV-33A6X / r435）

本目录用于记录 `fnnas_rockchip_sv-33a6x-vpu_k6.18.18_2026.09.23.img` 无法启动的分析与修复补丁。

## 结论

该镜像 0–16MB 引导区除 GPT 外全为 0，**没有任何 bootloader**。RK3399 BootROM 从 sector 64（0x8000）读 idbloader，该区域为 0 时直接停住，且 BootROM 阶段 UART 静默，因此表现为全程黑屏、串口无输出。

对镜像前 32MB 实测：`RK33` 未找到、FIT 魔数 `d00dfeed` 未找到、`U-Boot 20xx` 版本串未找到；0x8000 / 0x8800 / 8MB / 16MB 四处全为 `00`。同机刷官方 fnOS nanopc-t4 镜像则 `0x8800 = RK33`、`8MB = d00dfeed`、版本串 `U-Boot 2026.04-TRIM-c218`，可正常启动。

## 修复

### 1. 镜像层面（立即可用）

把板卡配套的 `u-boot-rockchip.bin`（9,522,688 字节，`U-Boot 2026.01-rc1`）写入镜像 sector 64：

```bash
dd if=u-boot-rockchip.bin of=<image>.img bs=512 seek=64 conv=fsync,notrunc
```

校验：`0x8000` 出现 loader 头、`0x8800` 为 `RK33`、`8MB` 为 `d00dfeed`。

注意镜像内 `extlinux/` 目录原本为空，需补一份 `extlinux/extlinux.conf`，否则即使有 loader 也会因为没有引导配置而失败。

### 2. 源码层面（防止复发）

`renas` 的 `make_image()` 中，rockchip 写 bootloader 的四个 `if/elif` 分支均以 `${uboot_path}/rockchip/${board}/${BOOTLOADER_IMG}` 文件存在为前提，且 `dd` 后面带 `2>/dev/null`。文件缺失时分支不成立、`dd` 不执行、错误被吞，镜像照常生成。

建议加一道写入后校验，不通过即 `error_msg` 中止：

```bash
if [[ "${PLATFORM}" == "rockchip" ]]; then
    if [[ "$(dd if="${loop_new}" bs=1 skip=34816 count=4 2>/dev/null)" != "RK33" ]]; then
        error_msg "Bootloader signature is missing at the 0x8800 offset of [ ${build_image_file} ], check [ ${bootloader_path}/${BOOTLOADER_IMG} ]."
    fi
fi
```

可用同目录下的 `patches/fix-renas-bootloader-check.py` 自动应用：

```bash
python3 patches/fix-renas-bootloader-check.py /path/to/fnnas
```

## 刷写注意

RKDevTool「下载镜像」页中，`Boot` 行（MiniLoaderAll.bin）只把 miniloader 送进 RAM 用于通信；随后 `system` 行从 `0x00000000` 整盘写入，会把 0–16MB 覆盖成镜像内容。工具显示“下载Boot成功”并不代表 flash 里有 loader。

---

<sub>本文由 DeepSeek 与 WorkBuddy 自动分析生成。</sub>
