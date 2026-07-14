# 数据字典

`evaluation-sample.csv` 为方法验证用合成样本。字段设计模拟离线评测所需的最小结构，不包含真实个人信息。

| 字段 | 类型 | 说明 |
|---|---:|---|
| record_id | string | 样本记录编号，必须唯一 |
| school_id | string | 合成学校编号 |
| class_id | string | 合成班级编号 |
| teacher_id | string | 合成教师编号 |
| assignment_id | string | 作业批次编号 |
| item_id | string | 题目编号 |
| student_id | string | 匿名学生编号 |
| grade | integer | 年级 |
| subject | string | 学科 |
| item_type | enum | `objective` 或 `subjective` |
| max_score | number | 题目满分 |
| model_score | number | 模型建议分 |
| teacher1_score | number | 教师一独立评分 |
| teacher2_score | number | 教师二独立评分 |
| adjudicated_score | number | 裁定分或客观题标准分 |
| model_correct | boolean | 模型是否在预设容许误差内 |
| confidence | number | 模型置信度，范围为 0 到 1 |
| threshold_version | string | 分流阈值版本 |
| risk_flag | string | 风险标记或人工关注原因 |
| route | enum | `auto_pass`、`sample_review`、`teacher_review`、`face_to_face` |
| review_completed | boolean | 是否完成教师复核 |
| severe_error | boolean | 是否属于预定义严重误判 |
| post_review_correct | boolean | 复核后结果是否正确 |
| baseline_time_sec | integer | 传统流程估计处理时间，合成值 |
| review_time_sec | integer | 本框架下处理时间，合成值 |
| knowledge_point | string | 对应知识点 |
| synthetic | boolean | 是否为合成数据，本仓库固定为 `true` |

## 解释限制

样本仅用于测试指标计算、字段校验和风险分流逻辑。由于没有真实抽样过程、盲评流程和学校环境，任何描述性数值都不能解释为产品效果。
