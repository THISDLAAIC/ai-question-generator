import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int


@dataclass
class ExamConfig:
    part1_count: int
    part1_topics: list[str]
    part2_count: int
    school_name: str
    club_name: str


@dataclass
class OutputConfig:
    dir: str


@dataclass
class AppConfig:
    llm: LLMConfig
    exam: ExamConfig
    output: OutputConfig


def _resolve_env(value: str) -> str:
    pattern = re.compile(r"\$\{(\w+)\}")
    matches = pattern.findall(value)
    for var in matches:
        env_val = os.environ.get(var, "")
        value = value.replace(f"${{{var}}}", env_val)
    return value


def load_config(path: str = "config.yaml") -> AppConfig:
    config_path = Path(__file__).parent / path
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    llm_raw = raw["llm"]
    llm_config = LLMConfig(
        base_url=_resolve_env(llm_raw["base_url"]),
        api_key=_resolve_env(llm_raw["api_key"]),
        model=llm_raw["model"],
        temperature=float(llm_raw.get("temperature", 0.9)),
        max_tokens=int(llm_raw.get("max_tokens", 4096)),
    )

    exam_raw = raw["exam"]
    output_raw = raw["output"]

    exam_config = ExamConfig(
        part1_count=exam_raw["part1"]["count"],
        part1_topics=exam_raw["part1"]["topics"],
        part2_count=exam_raw["part2"]["count"],
        school_name=output_raw.get("school_name", ""),
        club_name=output_raw.get("club_name", ""),
    )

    output_config = OutputConfig(dir=output_raw.get("dir", "./output"))

    missing = []
    if not llm_config.base_url:
        missing.append("llm.base_url")
    if not llm_config.api_key:
        missing.append("llm.api_key (或环境变量未设置)")
    if not llm_config.model:
        missing.append("llm.model")
    if missing:
        raise ValueError(f"配置缺失: {', '.join(missing)}")

    return AppConfig(llm=llm_config, exam=exam_config, output=output_config)
