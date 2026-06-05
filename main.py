import sys
import os
from datetime import datetime
from pathlib import Path

from config import load_config
from generator import QuestionGenerator
from exporter import build_markdown, build_answer_markdown, export_markdown, export_pdf


def main():
    config_path = "config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    print(f"=== AI 入团考题生成器 ===")
    print(f"配置文件: {config_path}")

    config = load_config(config_path)
    print(f"LLM: {config.llm.model} @ {config.llm.base_url}")

    generator = QuestionGenerator(config)

    try:
        part1, part2 = generator.generate_all()
    except Exception as e:
        print(f"[错误] 生成失败: {e}")
        sys.exit(1)

    school = config.exam.school_name
    club = config.exam.club_name

    exam_md = build_markdown(part1, part2, school, club)
    answer_md = build_answer_markdown(part1, part2, school, club)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(Path(__file__).parent / config.output.dir / ts)
    os.makedirs(output_dir, exist_ok=True)

    exam_path = export_markdown(exam_md, output_dir, prefix="试卷")
    answer_path = export_markdown(answer_md, output_dir, prefix="答案")

    print(f"\n=== 生成完成 ===")
    print(f"试卷: {exam_path}")
    print(f"答案: {answer_path}")

    try:
        export_pdf(exam_path, output_dir, prefix="试卷")
        export_pdf(answer_path, output_dir, prefix="答案")
    except Exception as e:
        print(f"[提示] PDF 导出跳过: {e}")


if __name__ == "__main__":
    main()
