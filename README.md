# AstrBot Personal Plugin Source

一个面向个人使用的 AstrBot 定向插件源。

本仓库不会镜像或再分发任何插件源码，只根据手动维护的 `watchlist.json` 生成一个 AstrBot 可读取的 `plugins.json`。它适合用于跟踪少量自己信任并实际使用的插件，减少等待官方插件源同步的时间。
主要用于快速更新至最新版本，为保持稳定，建议官方源更新后切换回去。

## 插件源地址

```text
https://MMMaoTS.github.io/astrbot-personal-plugin-source/plugins.json
```

## 当前跟踪插件

当前 `watchlist.json` 跟踪以下插件：

| 插件 ID                              | 仓库                                                             |
| ---------------------------------- | -------------------------------------------------------------- |
| `astrbot-plugin-private-companion` | `https://github.com/menglimi/astrbot_plugin_private_companion` |

## 工作方式

本仓库采用轻量输入、自动生成输出的结构：

```text
watchlist.json
    ↓
GitHub Actions
    ↓
scripts/build_plugins_json.py
    ↓
plugins.json
    ↓
GitHub Pages
```

其中：

* `watchlist.json`：只记录需要跟踪的插件 ID 和仓库地址。
* `scripts/build_plugins_json.py`：读取官方插件集合和插件仓库的 `metadata.yaml`，生成插件源。
* `plugins.json`：AstrBot 实际读取的插件源文件。
* GitHub Actions：定时更新 `plugins.json`，并在需要时提交到仓库。
* GitHub Pages：提供可被 AstrBot WebUI 访问的静态插件源地址。

## 添加新插件

编辑 `watchlist.json`，追加插件条目：

```json
{
  "plugins": [
    {
      "id": "astrbot-plugin-private-companion",
      "repo": "https://github.com/menglimi/astrbot_plugin_private_companion"
    }
  ]
}
```

字段说明：

* `id`：插件源中的插件 ID。若插件已经进入官方插件源，建议沿用官方 `plugins.json` 中的 key。
* `repo`：插件 GitHub 仓库地址。
* `branch`：可选。默认自动读取仓库默认分支。

提交后，GitHub Actions 会自动更新 `plugins.json`。也可以在 Actions 页面手动运行工作流。

## 在 AstrBot 中使用

在 AstrBot WebUI 中添加自定义插件源：

```text
名称：Personal Plugin Source
地址：https://MMMaoTS.github.io/astrbot-personal-plugin-source/plugins.json
```

建议从该自定义插件源安装插件，而不是直接使用 GitHub URL 安装。这样更容易保留插件源绑定关系，便于后续更新检测。

## 与官方插件源的关系

本仓库不是 AstrBot 官方插件源，也不是官方 `AstrBot_Plugins_Collection` 仓库的 fork。

本仓库仅用于个人定向索引，生成的 `plugins.json` 会参考：

* AstrBot 官方插件集合：`AstrBotDevs/AstrBot_Plugins_Collection`
* 插件仓库自身的 `metadata.yaml`
* 插件仓库自身的公开元数据

官方插件集合仓库见：

```text
https://github.com/AstrBotDevs/AstrBot_Plugins_Collection
```

AstrBot 插件开发文档见：

```text
https://docs.astrbot.app/dev/star/plugin-new.html
```

## 版权与许可声明

本仓库只维护个人插件索引生成逻辑，不镜像、不打包、不再分发第三方插件源码。

重要声明：

* AstrBot、AstrBot 插件集合及其相关商标、名称、代码归其原项目和贡献者所有。
* 被索引插件的名称、描述、Logo、源码、文档和元数据归各插件作者或其对应许可证约束。
* 本仓库中的插件条目仅作为链接和索引使用，不代表对插件安全性、稳定性、许可证兼容性作出保证。
* 安装插件前，请自行检查目标插件仓库的源码、依赖、权限行为和许可证。
* 若本仓库中的索引信息侵犯了你的权益，请提交 Issue 或联系仓库维护者处理。

## License

本仓库自身的脚本和配置以 GNU Affero General Public License v3.0 发布。

注意：本仓库的许可证只覆盖本仓库自身内容，不改变被索引插件的原始许可证。
