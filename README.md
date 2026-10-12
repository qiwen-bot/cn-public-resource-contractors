# 中国各地市公共资源交易系统承建公司统计

本仓库用于收集、整理中国各地市（含省本级、地市）**公共资源交易系统**的承建 / 建设厂商信息，便于检索与对比。

## 数据字段

见 `data/contractors.csv`，核心字段：

| 字段 | 说明 |
|------|------|
| province | 省 / 自治区 / 直辖市 |
| city | 地市或「省本级」 |
| system_name | 系统或平台名称 |
| system_url | 官网或入口 URL |
| contractor | 承建 / 建设公司 |
| contractor_uscc | 统一社会信用代码（如有） |
| contract_year | 建设或中标年份（如有） |
| source | 信息来源（公告、官网、新闻等） |
| notes | 备注 |
| updated_at | 更新日期（YYYY-MM-DD） |

## 使用方式

1. 在 `data/contractors.csv` 追加一行记录。
2. 尽量注明 `source`，便于复核。
3. 同一地市若有多期建设或更换厂商，保留多行并在 `notes` 说明。

## 许可

数据与文档以仓库内 LICENSE 为准；引用公开招标公告时请遵守原始来源的使用要求。
