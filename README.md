# AI 入团考题生成器

北京市海淀区稻香湖学校 · 应用人工智能社团

基于 LLM 自动生成社团入团考试卷，包含：

- **第一部分**：编程概念选择题（面向对象、函数式、异步、JSON），考察对编程范式的理解
- **第二部分**：理工科学习能力考查(大学化学/物理/生物概念)，实际只需初中代数即可求解

双向通过制：候选人在任一部分得分 ≥ 75% 即通过。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

PDF 导出需要 pandoc + xelatex（可选，无此依赖则回退到 weasyprint）：

```bash
brew install pandoc basictex
```

## 配置

编辑 `config.yaml`：

```yaml
llm:
  base_url: "https://your-api/v1"
  api_key: "sk-xxx"              # 支持 ${ENV_VAR} 环境变量
  model: "deepseek/deepseek-v4-pro"
  temperature: 0.5
  max_tokens: 40960

exam:
  part1:
    count: 10
    topics: ["面向对象编程 OOP", "函数式编程 FP", "异步编程 Async", "JSON 数据格式"]
  part2:
    count: 2

output:
  dir: "./output"
  school_name: "北京市海淀区稻香湖学校"
  club_name: "应用人工智能社团"
```

## 运行

```bash
./run.sh
# 或
.venv/bin/python3 main.py
# 指定自定义配置文件
.venv/bin/python3 main.py path/to/config.yaml
```

## 输出

每次运行在 `output/` 下生成时间戳目录，包含：

- `试卷.md` / `试卷.pdf` — 考试卷（含卷首语、两部分题目）
- `答案.md` / `答案.pdf` — 答案（含解析与分步求解过程）

历史文件 `output/question_history.json` 用于避免 Part 2 题目重复。
