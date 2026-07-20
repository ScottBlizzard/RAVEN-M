# Source and Verification Policy

## 状态标签

- `verified_primary`：已由官方 proceedings、出版社、OpenReview、作者主页、实验室主页、官方 GitHub 或模型卡确认。
- `verified_cross_source`：至少两个相互独立的一级来源一致。
- `preprint_only`：目前只确认 arXiv/技术报告，不写成正式录用。
- `manual_needed`：题录、代码归属或发布状态仍需人工确认。
- `download_failed`：来源成立，但本地抓取失败。

## 版本规则

- 网页记录访问日期。
- Git 仓库记录 URL、默认分支、HEAD commit 和抓取日期。
- PDF 记录 SHA-256。
- AndroidWorld task 数量、Hard 标签和 step budget 以实际冻结 commit 为准，不把动态网页当永久事实。
- Qwen 模型代码、processor、checkpoint revision 和量化方式分别锁定；“同名模型”不代表同一实验条件。

## 禁止事项

- 不把 GitHub README 的性能数字直接当成可比较实验结果。
- 不因项目名称相同而克隆非作者/论文链接的仓库。
- 不把 arXiv-only 工作写成顶会录用。
- 不在读取 Hard task 结果后修改 prompt、memory 阈值或主要实验定义。

