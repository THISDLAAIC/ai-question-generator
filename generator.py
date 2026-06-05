import json
from pathlib import Path

import requests

from config import AppConfig


def _load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


class QuestionGenerator:
    HISTORY_FILE = Path(__file__).parent / "output" / "question_history.json"

    def __init__(self, config: AppConfig):
        self.config = config
        self.base_url = config.llm.base_url.rstrip("/")
        self.api_key = config.llm.api_key
        self.model = config.llm.model
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.part1_system = _load_prompt("part1_system.txt")
        self.part2_system = _load_prompt("part2_system.txt")
        self._history: dict = self._load_history()

    def _load_history(self) -> dict:
        try:
            if self.HISTORY_FILE.exists():
                return json.loads(self.HISTORY_FILE.read_text("utf-8"))
        except Exception:
            pass
        return {"part2": []}

    def _save_history(self):
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.HISTORY_FILE.write_text(
            json.dumps(self._history, ensure_ascii=False, indent=2), "utf-8"
        )

    def _build_history_prompt(self) -> str:
        past = self._history.get("part2", [])
        if not past:
            return ""
        lines = ["\n\n【已出过的题目——请勿重复】"]
        lines.append("（注意：相同的背景概念可以复用，但子问题的题干不能雷同。）")
        for i, item in enumerate(past, 1):
            title = item.get("title", "")
            subject = item.get("subject", "")
            subs = item.get("sub_questions", [])
            lines.append(f"{i}. [{subject}] {title}")
            for sq in subs:
                lines.append(f"   - {sq.get('question', '')[:80]}")
        return "\n".join(lines)

    def _call_llm_stream(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        resp = requests.post(
            url, json=payload, headers=headers, timeout=600,
            proxies={"http": None, "https": None}, stream=True,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"API 返回 {resp.status_code}: {resp.text[:500]}"
            )

        content_parts = []
        reasoning_started = False
        content_started = False
        for line in resp.iter_lines(decode_unicode=False):
            if not line:
                continue
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                reasoning = delta.get("reasoning_content", "")
                c = delta.get("content", "")
                if reasoning:
                    if not reasoning_started:
                        print("\n[思考过程] ", end="", flush=True)
                        reasoning_started = True
                    print(reasoning, end="", flush=True)
                if c:
                    if not content_started:
                        if reasoning_started:
                            print("")
                        print("[生成内容] ", end="", flush=True)
                        content_started = True
                    content_parts.append(c)
                    print(c, end="", flush=True)
            except json.JSONDecodeError:
                continue

        print("")
        content = "".join(content_parts).strip()
        if not content:
            raise RuntimeError("流式响应未返回任何内容")
        return content

    def _parse_json(self, raw: str, context: str) -> list:
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = lines[1:] if lines else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)

        for attempt, text in enumerate([raw] + self._try_repair(raw)):
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    pass
                continue

        debug_path = Path(__file__).parent / "output" / f"_debug_{context.replace(' ', '_')}.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(raw, encoding="utf-8")
        raise ValueError(
            f"{context}: 无法解析 LLM 返回的 JSON，"
            f"原始内容已保存到 {debug_path}，"
            f"前500字符: {raw[:500]}..."
        )

    def _try_repair(self, raw: str):
        results = []
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            results.append(raw[start : end + 1])
        import re
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            results.append(m.group())
        return results

    def _fix_count(self, raw: str, expected: int, actual: int, context: str) -> str:
        correction = (
            f"你刚才输出了 {actual} 道题，但要求是 {expected} 道。"
            f"请修正，只输出完整的 JSON 数组，确保恰好 {expected} 道题。"
        )
        print(f"  [修正] 数量不对（{actual}/{expected}），让 AI 修正...")
        return self._call_llm_stream(
            f"你之前的输出有误。{correction}。之前的内容供参考：\n{raw[:2000]}",
            correction,
        )

    def generate_part1(self) -> list[dict]:
        expected = self.config.exam.part1_count
        user_prompt = (
            f"请生成 {expected} 道选择题，"
            f"均匀覆盖以下方向：{', '.join(self.config.exam.part1_topics)}。"
            "记住：所有选项必须合理，干扰项基于常见误解。"
        )
        print("[Part 1] 正在生成选择题（流式）...")
        raw = self._call_llm_stream(self.part1_system, user_prompt)

        for retry in range(3):
            questions = self._parse_json(raw, "Part 1")
            if len(questions) == expected:
                break
            print(f"  [Part 1] 数量不对：期望 {expected}，得到 {len(questions)}，第 {retry+1} 次修正")
            if retry < 2:
                raw = self._fix_count(raw, expected, len(questions), "Part 1")
        else:
            questions = self._parse_json(raw, "Part 1")

        if len(questions) != expected:
            print(
                f"[Part 1] 警告：期望 {expected} 题，"
                f"实际 {len(questions)} 题，已尽力修正"
            )
        print(f"[Part 1] 成功生成 {len(questions)} 道选择题")
        return questions

    def generate_part2(self) -> list[dict]:
        expected = self.config.exam.part2_count
        user_prompt = (
            f"请生成 {expected} 道情境阅读大题，"
            "每题 2-3 个子问题，总分约 25 分。每道大题选自不同领域（只能选物理、化学、生物）。"
        )
        history = self._build_history_prompt()
        if history:
            user_prompt += history
        print("[Part 2] 正在生成情境题（流式）...")
        raw = self._call_llm_stream(self.part2_system, user_prompt)

        for retry in range(3):
            questions = self._parse_json(raw, "Part 2")
            if len(questions) == expected:
                break
            print(f"  [Part 2] 数量不对：期望 {expected}，得到 {len(questions)}，第 {retry+1} 次修正")
            if retry < 2:
                raw = self._fix_count(raw, expected, len(questions), "Part 2")
        else:
            questions = self._parse_json(raw, "Part 2")

        if len(questions) != expected:
            print(
                f"[Part 2] 警告：期望 {expected} 题，"
                f"实际 {len(questions)} 题，已尽力修正"
            )
        print(f"[Part 2] 成功生成 {len(questions)} 道情境题")

        for q in questions:
            self._history["part2"].append({
                "title": q.get("title", ""),
                "subject": q.get("subject", ""),
                "sub_questions": [
                    {"question": sq.get("question", "")}
                    for sq in q.get("sub_questions", [])
                ],
            })
        self._save_history()
        return questions

    def generate_all(self) -> tuple[list[dict], list[dict]]:
        part1 = self.generate_part1()
        part2 = self.generate_part2()
        return part1, part2
