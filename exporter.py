import os
import shutil
import subprocess


def _safe(val, default=""):
    return val if val is not None else default


def build_markdown(part1: list[dict], part2: list[dict], school: str, club: str) -> str:
    part1_score = sum(5 for _ in part1)
    part2_score = 50
    passing = int(part1_score * 0.75)

    lines = []

    lines.append(f"# {school} {club}招新测试")
    lines.append("")
    lines.append("## 【卷首语：阅读说明】")
    lines.append("")
    lines.append("欢迎报名应用人工智能社团！本试卷旨在发掘不同维度的人才。我们深知，优秀的 AI 开发者既需要扎实的工程基础，也需要极强的逻辑建模和快速学习能力。")
    lines.append("")
    lines.append(f"**双轨制评分：** 本试卷分为两部分，第一部分 {part1_score} 分，第二部分 {part2_score} 分。任意一部分得分超过 {passing} 分（75%）即视为通过测试！")
    lines.append("")
    lines.append("**答题策略：** 遇到没见过的概念不要慌张。如果你有编程基础，请主攻第一部分；如果你逻辑严密、学东西快，请主攻第二部分。选定你的优势方向，秀出你最强的一面。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## 第一部分：编程基本概念与理解（共 {part1_score} 分）")
    lines.append("")
    lines.append(f"本部分共 {len(part1)} 题，每题 5 分。本部分不涉及特定编程语言的代码书写，仅考察你对计算机科学核心思想和数据结构的直觉。")
    lines.append("")

    for idx, q in enumerate(part1, 1):
        topic = _safe(q.get("topic"), "编程概念")
        lines.append(f"### {idx}. 【{topic}】")
        lines.append("")
        lines.append(_safe(q.get("question")))
        lines.append("")
        for opt in q.get("options", []):
            lines.append(f"- **{opt['label']}.** {opt['text']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"## 第二部分：理工科学习能力考查（共 {part2_score} 分）")
    lines.append("")
    lines.append(f"本部分包含 {len(part2)} 道情境阅读大题。题目中所涉及的概念均为大学前沿知识，你不需要有任何相关前置知识，所有解题需要的规则和定义均已在题干中给出。请阅读规则后进行逻辑推演。**所有题目请写出严谨的论证过程，明确引用题干中的规则逐步推导。**")
    lines.append("")

    for idx, q in enumerate(part2, 1):
        subject = _safe(q.get("subject"), "综合")
        title = _safe(q.get("title"), f"题目{idx}")
        label = chr(64 + idx)
        lines.append(f"### 题目 {label}：{title}（{subject}，25 分）")
        lines.append("")
        lines.append("**【背景规则】**")
        lines.append("")
        lines.append(_safe(q.get("background")))
        lines.append("")

        for sq in q.get("sub_questions", []):
            num = sq.get("number", "?")
            sq_text = _safe(sq.get("question"))
            score = sq.get("score", "?")
            lines.append(f"**【问题{num}】（{score} 分）**")
            lines.append("")
            lines.append(sq_text)
            lines.append("")
            lines.append("")
            lines.append("")

    return "\n".join(lines)


def build_answer_markdown(part1: list[dict], part2: list[dict], school: str, club: str) -> str:
    lines = []
    lines.append(f"# {school} {club}招新测试 —— 参考答案与解析")
    lines.append("")
    lines.append("## 第一部分：选择题答案与解析")
    lines.append("")

    for idx, q in enumerate(part1, 1):
        topic = _safe(q.get("topic"), "编程概念")
        correct = _safe(q.get("correct"), "?")
        explanation = _safe(q.get("explanation"), "暂无解析")
        lines.append(f"### {idx}. 【{topic}】")
        lines.append(f"**答案：{correct}**")
        lines.append("")
        lines.append(f"{explanation}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 第二部分：情境题参考答案")
    lines.append("")

    for idx, q in enumerate(part2, 1):
        title = _safe(q.get("title"), f"题目{idx}")
        label = chr(64 + idx)
        lines.append(f"### 题目 {label}：{title}")
        lines.append("")
        for sq in q.get("sub_questions", []):
            num = sq.get("number", "?")
            answer = _safe(sq.get("answer"), "略")
            lines.append(f"**【问题{num}参考答案】**")
            lines.append("")
            lines.append(answer)
            lines.append("")

    return "\n".join(lines)


def export_markdown(content: str, output_dir: str, prefix: str = "入团测试") -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{prefix}.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[输出] Markdown 已保存: {filepath}")
    return filepath


def export_pdf(md_path: str, output_dir: str, prefix: str = "入团测试") -> str:
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"{prefix}.pdf")

    if shutil.which("xelatex") and shutil.which("pandoc"):
        try:
            subprocess.run(
                ["pandoc", md_path, "-o", pdf_path,
                 "--pdf-engine=xelatex",
                 "-V", "mainfont=Heiti SC",
                 "-V", "CJKmainfont=Heiti SC",
                 "-V", "geometry:margin=2cm",
                 "-V", "fontsize=12pt"],
                check=True, capture_output=True, text=True, timeout=120,
            )
            print(f"[输出] PDF 已保存: {pdf_path}")
            return pdf_path
        except subprocess.CalledProcessError as e:
            print(f"[输出] xelatex 失败: {e.stderr[:200]}")

    return _export_pdf_weasyprint(md_path, output_dir, prefix)


def _export_pdf_weasyprint(md_path: str, output_dir: str, prefix: str) -> str:
    import markdown
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    html_content = markdown.markdown(md_content, extensions=["extra", "codehilite", "toc"])
    css = """
    @page { size: A4; margin: 2cm; }
    body { font-family: "PingFang SC", "Heiti SC", "STHeiti", "Microsoft YaHei", sans-serif; font-size: 12pt; line-height: 1.8; color: #222; }
    h1 { font-size: 18pt; text-align: center; margin-bottom: 0.5em; }
    h2 { font-size: 15pt; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; margin-top: 1.2em; }
    h3 { font-size: 13pt; margin-top: 1em; }
    hr { border: none; border-top: 1px dashed #ccc; margin: 1.5em 0; }
    pre, code { background: #f5f5f5; padding: 0.1em 0.3em; border-radius: 3px; font-size: 10pt; }
    pre { padding: 0.8em; overflow-x: auto; }
    strong { color: #c00; }
    """
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
{html_content}
</body>
</html>"""
    pdf_path = os.path.join(output_dir, f"{prefix}_{ts}.pdf")
    try:
        from weasyprint import HTML
        HTML(string=full_html).write_pdf(pdf_path)
        print(f"[输出] PDF 已保存: {pdf_path}")
    except ImportError:
        print("[输出] weasyprint 未安装，跳过 PDF 生成")
        pdf_path = ""
    return pdf_path
