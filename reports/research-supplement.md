# 研究补充材料索引

本目录保存与主文档配套的补充材料。材料目的在于说明方案的研究深度、指标可复现性和治理边界，不用于证明真实产品效果。

## 材料构成

| 材料 | 位置 | 用途 |
|---|---|---|
| 系统架构图 | `assets/system-architecture.svg` | 概括作业采集、学科理解、风险分流、教师复核、订正反馈和治理约束之间的关系 |
| 合成评测输出 | `reports/synthetic-evaluation-report.json` | 固化一次可复现指标计算结果，便于审阅者核对脚本输出 |
| 合成样本 | `data/evaluation-sample.csv` | 演示字段结构、风险路径和评测指标计算 |
| 数据字典 | `data/DATA_DICTIONARY.md` | 解释样本字段、类型和使用限制 |
| 评测脚本 | `analysis/evaluate.py` | 计算教师一致性、模型误差、自动通过覆盖率、错误捕获率和严重错误逃逸率 |
| 单元测试 | `tests/test_evaluate.py` | 验证字段校验、重复样本、零分母和非上线授权逻辑 |

## 复现说明

评测报告由以下命令生成：

```bash
python analysis/evaluate.py data/evaluation-sample.csv
```

测试由以下命令执行：

```bash
python -m unittest discover -s tests -v
```

## 解释边界

`synthetic-evaluation-report.json` 中的所有结果均来自合成样本。其作用是证明评测口径可以被复现，而不是证明系统达到某一准确率、节时比例或学习收益。真实教学效应需要在预注册、分集群随机上线和独立盲评金标准条件下估计。
