# WebCrawler Fixed

## 项目说明

本项目参考开源项目 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 进行二次开发，保留其多平台公开数据采集、浏览器登录态复用、命令行启动和多种存储方式等基础能力。

当前仓库不是原项目官方版本，主要目标是在原项目基础上补充新的平台适配、情报导出接口、存储增强和测试覆盖，便于后续接入黑灰产情报分析流程。

## 主要改进与扩展

- **新增 X 平台支持**：增加 `x` 平台命令行入口、浏览器采集流程、搜索结果解析、评论采集、数据模型和本地存储实现。
- **新增闲鱼支持**：增加 `goofish`/闲鱼平台配置、搜索采集、详情解析、评论/商品数据处理、创作者参数归一化和独立存储实现。
- **黑灰产情报标准化导出 API**：新增 `GET /api/black-gray-intel/records`，可将抖音、贴吧、小红书、X、闲鱼的本地 JSONL 结果转换为统一字段，保留来源、作者、正文、媒体链接和扩展元数据。
- **贴吧与小红书适配增强**：补充贴吧登录、搜索、详情、评论和创作者链接处理；增加小红书风控暂停重试配置，降低登录或滑块校验异常对任务的影响。
- **存储能力增强**：补充 JSONL 换行清洗、CSV/JSON/JSONL 本地去重、Excel 导出统一收尾写入，以及多平台图片 URL 和评论字段保留。
- **命令行参数扩展**：扩展 `--platform`、`--specified_id_list`、`--creator_id_list` 等参数对 X、贴吧和闲鱼的支持，并对常见 ID/URL 输入做归一化。
- **测试覆盖补充**：新增 X、闲鱼、贴吧、黑灰产 API、存储去重、Excel 导出和异步文件写入等测试用例，覆盖新增平台和数据出口的关键路径。

## 使用提示

安装依赖后，可通过命令行查看当前支持的平台和参数：

```bash
python main.py --help
```

常见入口示例：

```bash
# 启动小红书搜索采集
python main.py --platform xhs --lt qrcode --type search

# 启动闲鱼搜索采集
python main.py --platform goofish --lt qrcode --type search --keywords "手机,显卡"

# 启动 API 服务后读取标准化情报记录
python -m uvicorn api.main:app --host 127.0.0.1 --port 18080
curl "http://127.0.0.1:18080/api/black-gray-intel/records?platform=xhs&kind=all&date=latest&limit=100"
```

更多运行方式请以 `python main.py --help`、各平台配置文件和源码中的参数定义为准。

## 合规声明

本项目仅用于学习、研究和合规的数据处理验证。使用者应遵守目标平台服务条款、robots.txt、相关法律法规以及原项目许可证要求，不得用于商业化爬取、大规模抓取、侵犯他人权益或任何违法违规用途。
