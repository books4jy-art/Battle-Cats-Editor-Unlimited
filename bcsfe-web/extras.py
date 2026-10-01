"""More BCSFE edits for the web editor.

Forms & talents, special skills, Ototo, Gamatoto & cat shrine, endless battle items,
extra stages & scores, account progress and repair tools. `parse()` turns the web
form into an edits dict (used by app.py); `apply()` runs those edits on a loaded save
(used by worker.py). Each edit mirrors what the BCSFE CLI does for the same menu item,
minus the interactive questions.
"""
from __future__ import annotations

import datetime
import math
import random
from typing import Any, Callable

LANG = "en"

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "forms": "Forms & talents",
        "true_evolve": "True form for {n} characters",
        "levels_raised": " (levels raised to what the form needs for {n})",
        "true_force": "True form forced for {n} characters",
        "true_remove": "True form removed from {n} characters",
        "fourth_evolve": "4th form for {n} characters",
        "fourth_force": "4th form forced for {n} characters",
        "fourth_remove": "4th form removed from {n} characters",
        "talents_max": "Talents maxed for {n} characters",
        "talents_remove": "Talents reset for {n} characters",
        "guide_add": "Cat guide: {n} characters collected",
        "guide_remove": "Cat guide: {n} characters removed",
        "no_cats": "no owned characters to change",
        "skills": "Special skills: {n} set to {level}",
        "engineers": "Engineers set to {n}",
        "cannons": "All {n} cat cannons maxed",
        "gamatoto_level": "Gamatoto level set to {n}",
        "helpers": "Gamatoto helpers set ({n} total)",
        "shrine": "Cat shrine level set to {n}",
        "shrine_show": "Cat shrine made to appear",
        "endless": "Endless battle items: {n} set to {time}",
        "infinite": "infinite",
        "minutes": "{n} min",
        "aku_realm": "Aku realm unlocked",
        "tutorial": "Tutorial cleared",
        "aku_chapters": "Aku chapter cleared ({n} stages)",
        "outbreaks": "Zombie outbreaks cleared ({n} stages)",
        "filibuster": "Filibuster stage re-clearing allowed",
        "score_challenge": "Challenge score set to {n}",
        "score_dojo": "Dojo score set to {n}",
        "score_itf": "ItF timed scores set to {n}",
        "slots": "Lineup slots set to {n}",
        "playtime": "Playtime set to {n} hours",
        "rank_claim": "User rank rewards: {n} marked claimed",
        "rank_fix": "User rank rewards: {n} wrongly claimed rewards fixed",
        "medals_add": "Meow medals: {n} added",
        "medals_remove": "Meow medals: {n} removed",
        "missions_reward": "Missions: {n} completed (reward ready)",
        "missions_claimed": "Missions: {n} completed and claimed",
        "missions_reset": "Missions: {n} reset",
        "enemy_add": "Enemy guide: {n} enemies unlocked",
        "enemy_remove": "Enemy guide: {n} enemies removed",
        "gold_give": "Gold pass given for 30 days",
        "gold_remove": "Gold pass removed",
        "restart_pack": "Restart pack made available",
        "gambling": "Wildcat slots and cat scratcher reset",
        "golden_cpu": "Golden Cat CPU uses reset",
        "fix_gamatoto": "Fixed: Gamatoto crash",
        "fix_ototo": "Fixed: Ototo crash",
        "fix_time": "Fixed: time errors",
        "fix_equip": "Fixed: equip menu unlocked",
        "fix_officer": "Fixed: officer pass crash",
        "fix_limits": "Fixed: {n} values over the game's limits capped",
        "fix_levels": "Fixed: levels of {n} characters brought within their limits",
        "fix_forms": "Fixed: forms of {n} characters",
        "fix_lineups": "Fixed: {n} lineup slots with characters you don't own emptied",
        "no_data": "couldn't download game data — try again later",
        "nothing": "nothing to change in this save",
        # parse errors
        "bad_choice": "Unknown option.",
        "bad_number": "Numbers must be whole numbers.",
        "bad_level": "Type the level like 50+10, 30, +20 or max.",
        "need_pick": "Pick at least one type, or choose All types.",
        "need_form_pick": "Pick characters with the Lv button, or choose All owned.",
        # catalog
        "rarity": "Rarity {n}",
    },
    "ko": {
        "forms": "형태 · 본능",
        "true_evolve": "캐릭터 {n}개 제3형태 진화",
        "levels_raised": " (진화에 필요한 레벨로 {n}개 레벨업)",
        "true_force": "캐릭터 {n}개 제3형태 강제 진화",
        "true_remove": "캐릭터 {n}개 제3형태 해제",
        "fourth_evolve": "캐릭터 {n}개 제4형태 진화",
        "fourth_force": "캐릭터 {n}개 제4형태 강제 진화",
        "fourth_remove": "캐릭터 {n}개 제4형태 해제",
        "talents_max": "캐릭터 {n}개 본능 최대",
        "talents_remove": "캐릭터 {n}개 본능 초기화",
        "guide_add": "캐릭터 도감: {n}개 등록",
        "guide_remove": "캐릭터 도감: {n}개 해제",
        "no_cats": "바꿀 보유 캐릭터가 없어요",
        "skills": "특수 강화: {n}종류를 {level}(으)로 설정",
        "engineers": "기술자 {n}명으로 설정",
        "cannons": "냥코 대포 {n}종류 최대 강화",
        "gamatoto_level": "가마토토 레벨 {n}(으)로 설정",
        "helpers": "가마토토 대원 설정 (총 {n}명)",
        "shrine": "고양이 신사 레벨 {n}(으)로 설정",
        "shrine_show": "고양이 신사 다시 나타나게 함",
        "endless": "배틀 아이템 무제한: {n}종류 {time}",
        "infinite": "무한",
        "minutes": "{n}분",
        "aku_realm": "악마 영역 해금",
        "tutorial": "튜토리얼 클리어",
        "aku_chapters": "악마편 클리어 (스테이지 {n}개)",
        "outbreaks": "좀비 습격 클리어 (스테이지 {n}개)",
        "filibuster": "필리버스터 스테이지 재클리어 가능",
        "score_challenge": "챌린지 배틀 점수 {n}(으)로 설정",
        "score_dojo": "도장 점수 {n}(으)로 설정",
        "score_itf": "미래편 타임 스코어 {n}(으)로 설정",
        "slots": "편성 슬롯 {n}개로 설정",
        "playtime": "플레이 시간 {n}시간으로 설정",
        "rank_claim": "유저 랭크 보상: {n}개 받음 처리",
        "rank_fix": "유저 랭크 보상: 잘못 받음 처리된 {n}개 수정",
        "medals_add": "냥코 메달: {n}개 추가",
        "medals_remove": "냥코 메달: {n}개 삭제",
        "missions_reward": "미션: {n}개 달성 (보상 받기 가능)",
        "missions_claimed": "미션: {n}개 달성 및 보상 받음",
        "missions_reset": "미션: {n}개 초기화",
        "enemy_add": "적 도감: {n}개 등록",
        "enemy_remove": "적 도감: {n}개 해제",
        "gold_give": "골드 회원 30일 지급",
        "gold_remove": "골드 회원 해지",
        "restart_pack": "재시작 팩 구매 가능",
        "gambling": "와일드캣 슬롯 · 고양이 스크래처 초기화",
        "golden_cpu": "골든 야옹컴 사용 횟수 초기화",
        "fix_gamatoto": "수리: 가마토토 오류",
        "fix_ototo": "수리: 오토토 오류",
        "fix_time": "수리: 시간 오류",
        "fix_equip": "수리: 편성 메뉴 해금",
        "fix_officer": "수리: 사원 명부 오류",
        "fix_limits": "수리: 게임 한도를 넘은 값 {n}개를 한도로 맞춤",
        "fix_levels": "수리: 캐릭터 {n}개의 레벨을 한도 안으로 맞춤",
        "fix_forms": "수리: 캐릭터 {n}개의 형태",
        "fix_lineups": "수리: 없는 캐릭터가 든 편성 칸 {n}개 비움",
        "no_data": "게임 데이터를 내려받지 못했어요 — 나중에 다시 시도하세요",
        "nothing": "이 세이브에는 바꿀 내용이 없어요",
        "bad_choice": "알 수 없는 옵션이에요.",
        "bad_number": "숫자는 정수로 입력하세요.",
        "bad_level": "레벨은 50+10, 30, +20 또는 최대처럼 입력하세요.",
        "need_pick": "종류를 하나 이상 고르거나 모든 종류를 선택하세요.",
        "need_form_pick": "Lv 버튼으로 캐릭터를 고르거나 보유한 모든 캐릭터를 선택하세요.",
        "rarity": "{n}등급",
    },
}


def t(key: str, **kwargs: Any) -> str:
    return TEXT[LANG][key].format(**kwargs)


MAX_WORDS = ("max", "최대")
FORM_CHOICES = {"true": ("evolve", "force", "remove"), "fourth": ("evolve", "force", "remove"),
                "talents": ("max", "remove"), "guide": ("add", "remove")}
PROGRESS_CHOICES = {"rank_rewards": ("claim", "fix"), "medals": ("add", "remove"),
                    "missions": ("reward", "claimed", "reset"), "enemy_guide": ("add", "remove"),
                    "gold_pass": ("give", "remove")}
PROGRESS_FLAGS = ("restart_pack", "reset_gambling", "reset_golden_cpu")
FIXES = ("fix_gamatoto", "fix_ototo", "fix_time", "fix_equip", "fix_officer",
         "fix_limits", "fix_levels", "fix_forms", "fix_lineups")
def _outbreak_layout() -> dict[int, list[int]]:
    """Zombie outbreak chapters and stage ids of the full game, from stage_shapes.json.gz (read from a
    real save with every outbreak); 9 chapters of 48 stages if that file is missing."""
    import gzip
    import json
    import os

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stage_shapes.json.gz")
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            chapters = json.load(fh)["tables"]["outbreaks"]["chapters"]
        layout = {int(cid): sorted(int(sid) for sid in stages) for cid, stages in chapters.items()}
        if layout:
            return layout
    except Exception:  # noqa: BLE001
        pass
    return {cid: list(range(48)) for cid in (0, 1, 2, 4, 5, 6, 7, 8, 9)}


STAGE_FLAGS = ("aku_realm", "aku_chapters", "outbreaks", "filibuster", "tutorial")
SCORES = ("challenge", "dojo", "itf")


# --------------------------------------------------------------------- parse ----
def _ids(raw: str, limit: int = 5000) -> list[int] | None:
    out: set[int] = set()
    for part in raw.replace(" ", "").split(","):
        if not part:
            continue
        lo, sep, hi = part.partition("-")
        if not lo.isdigit() or (sep and not hi.isdigit()):
            return None
        a, b = int(lo), int(hi) if sep else int(lo)
        if a > b or b >= limit:
            return None
        out.update(range(a, b + 1))
    return sorted(out)


def _num(raw: str | None, allow_max: bool = False, limit: int = 2_000_000_000) -> Any:
    """'' -> None, 'max' -> 'max', digits -> int, anything else -> ValueError."""
    raw = (raw or "").strip().replace(",", "").lower()
    if not raw:
        return None
    if allow_max and raw in MAX_WORDS:
        return "max"
    if not raw.isdigit():
        raise ValueError(raw)
    return min(int(raw), limit)


def _level(text: str) -> tuple[Any, Any] | None:
    base_s, sep, plus_s = text.replace(" ", "").lower().partition("+")

    def part(s: str, low: int) -> Any:
        if s in MAX_WORDS:
            return "max"
        if s.isdigit() and low <= int(s) <= 65536:
            return int(s)
        raise ValueError(s)

    try:
        base = part(base_s, 1) if base_s else None
        plus = part(plus_s, 0) if sep and plus_s else None
    except ValueError:
        return None
    return None if base is None and plus is None else (base, plus)


def parse(form: Any) -> dict[str, Any] | str:
    """Read the extra edit fields from the web form. Returns edits or an error message."""
    edits: dict[str, Any] = {}
    on = lambda key: form.get(key) in ("1", "true", "on")  # noqa: E731
    try:
        # forms & talents
        forms = {k: form.get(f"form_{k}") for k in FORM_CHOICES if form.get(f"form_{k}")}
        if any(v not in FORM_CHOICES[k] for k, v in forms.items()):
            return t("bad_choice")
        if forms:
            target = form.get("form_target") or "all"
            ids = _ids(form.get("form_ids") or "") if target == "picked" else []
            if target not in ("all", "picked") or ids is None or (target == "picked" and not ids):
                return t("need_form_pick")
            edits["forms"] = {**forms, "target": target, "ids": ids}

        # special skills: "50+10" for all or picked skills
        if (form.get("skill_level") or "").strip():
            level = _level(form.get("skill_level") or "")
            if level is None:
                return t("bad_level")
            ids = _ids(form.get("skill_ids") or "", 50)
            if ids is None or (form.get("skill_mode") == "pick" and not ids):
                return t("need_pick")
            edits["skills"] = {"base": level[0], "plus": level[1], "all": form.get("skill_mode") != "pick", "ids": ids}

        # ototo
        ototo = {"engineers": _num(form.get("engineers"), True, 999), "max_cannons": on("max_cannons")}
        if ototo["engineers"] is not None or ototo["max_cannons"]:
            edits["ototo"] = ototo

        # gamatoto & cat shrine
        helpers_raw = (form.get("gama_helpers") or "").strip()
        helpers = [(_num(x, False, 999) or 0) for x in helpers_raw.split(",")] if helpers_raw else None
        gama = {"level": _num(form.get("gama_level"), True, 9999), "helpers": helpers,
                "shrine": _num(form.get("shrine_level"), True, 9999), "shrine_show": on("shrine_show")}
        if any(v not in (None, False) for v in gama.values()):
            edits["gamatoto"] = gama

        # endless battle items
        endless = (form.get("endless_minutes") or "").strip().lower()
        if endless:
            minutes: Any = "inf" if endless in ("inf", "infinite", "무한") else _num(endless, False, 10_000_000)
            ids = _ids(form.get("endless_ids") or "", 50)
            if ids is None or not ids:
                return t("need_pick")
            edits["endless"] = {"minutes": minutes, "ids": ids}

        # extra stages & scores
        stages = {k: True for k in STAGE_FLAGS if on(k)}
        scores = {k: _num(form.get(f"score_{k}")) for k in SCORES}
        stages.update({f"score_{k}": v for k, v in scores.items() if v is not None})
        if stages:
            edits["more_stages"] = stages

        # progress
        progress: dict[str, Any] = {k: form.get(k) for k in PROGRESS_CHOICES if form.get(k)}
        if any(v not in PROGRESS_CHOICES[k] for k, v in progress.items()):
            return t("bad_choice")
        progress.update({k: True for k in PROGRESS_FLAGS if on(k)})
        slots, hours = _num(form.get("slots"), True, 99), _num(form.get("playtime_hours"), False, 999_999)
        if slots is not None:
            progress["slots"] = slots
        if hours is not None:
            progress["playtime_hours"] = hours
        if progress:
            edits["progress"] = progress

        fixes = [k for k in FIXES if on(k)]
        if fixes:
            edits["fixes"] = fixes
    except ValueError:
        return t("bad_number")
    return edits


# --------------------------------------------------------------------- apply ----
def catalog(core: Any, cc: Any) -> dict[str, Any]:
    """Names and limits for the extra sections, from the newest game data for a region."""
    save = core.SaveFile(cc=cc, load=False, gv=core.GameVersion(999999))
    names = core.core_data.get_gatya_item_names(save)
    buy = core.core_data.get_gatya_item_buy(save)
    skills = [[i, names.get_name(it.id) or f"#{i}"] for i, it in enumerate(buy.get_by_category(2) or [])]
    ability = core.core_data.get_ability_data(save).ability_data or []
    members = core.core_data.get_gamatoto_members_name(save)
    levels = core.core_data.get_gamatoto_levels(save)
    shrine = core.core_data.get_cat_shrine_levels(save)
    rarities = members.get_all_rarity_names() or []
    return {
        "ok": True,
        "skills": skills,
        "skill_max": [[a.max_base_level, a.max_plus_level] for a in ability],
        "helper_rarities": [r or t("rarity", n=i + 1) for i, r in enumerate(rarities)],
        "helpers_max": levels.get_total_helpers() or 0,
        "gamatoto_max": levels.get_max_level() or 0,
        "shrine_max": shrine.get_max_level() or 0,
        "engineers_max": core.Ototo.get_max_engineers(save),
        "engineers_name": names.get_name(92) or "",
    }


class Runner:
    """Runs one labelled edit through the worker's attempt() and keeps its result label."""

    def __init__(self, attempt: Callable[[str, Callable[[], None]], None], done: list[str]):
        self.attempt, self.done = attempt, done

    def __call__(self, label: str, fn: Callable[[], str | list[str]]) -> None:
        out: dict[str, Any] = {}
        before = len(self.done)
        self.attempt(label, lambda: out.update(result=fn()))
        if len(self.done) > before and out.get("result"):
            result = out["result"]
            self.done[-1:] = result if isinstance(result, list) else [result]


Step = "tuple[str, Callable[[], str]]"


def apply(core: Any, save: Any, edits: dict[str, Any], attempt: Callable, done: list[str]) -> None:
    """Run every requested extra edit as its own step, so one failing part doesn't stop the rest."""
    run = Runner(attempt, done)
    steps: list[Any] = []
    if edits.get("forms"):
        steps += _forms(core, save, edits["forms"], edits.get("remove_cats") or [])
    if edits.get("skills"):
        steps.append((t("skills", n="", level="").split(":")[0], lambda: _skills(core, save, edits["skills"])))
    if edits.get("ototo"):
        steps += _ototo(core, save, edits["ototo"])
    if edits.get("gamatoto"):
        steps += _gamatoto(core, save, edits["gamatoto"])
    if edits.get("endless"):
        steps.append((t("endless", n="", time="").split(":")[0], lambda: _endless(save, edits["endless"])))
    if edits.get("more_stages"):
        steps += _more_stages(core, save, edits["more_stages"])
    if edits.get("progress"):
        steps += _progress(core, save, edits["progress"])
    if edits.get("fixes"):
        steps += _fixes(core, save, edits["fixes"])
    for label, fn in steps:
        run(label, fn)


def _forms(core: Any, save: Any, spec: dict[str, Any], skip: list[int]) -> list[Any]:
    """Forms, talents and cat guide for all owned or picked characters: one step per change."""
    def cats() -> list[Any]:
        if spec["target"] == "all":
            chosen = save.cats.get_unlocked_cats()
        else:
            chosen = [c for c in (save.cats.get_cat_by_id(i) for i in spec["ids"]) if c is not None]
        chosen = [c for c in chosen if c.id not in skip]
        if not chosen:
            raise RuntimeError(t("no_cats"))
        return chosen

    set_forms = core.core_data.config.get_bool(core.ConfigKey.SET_CAT_CURRENT_FORMS)
    steps: list[Any] = []

    def forms(kind: str, how: str) -> str:
        chosen = cats()
        if how == "remove":
            for cat in chosen:
                (cat.remove_true_form if kind == "true" else cat.remove_fourth_form)()
            return t(f"{kind}_{how}", n=len(chosen))
        before = {cat.id: (cat.unlocked_forms, cat.fourth_form) for cat in chosen}
        if kind == "true":
            save.cats.true_form_cats(save, chosen, how == "force", set_forms)
        else:
            save.cats.fourth_form_cats(save, chosen, how == "force", set_forms)
        evolved = [cat for cat in chosen if (cat.unlocked_forms, cat.fourth_form) != before[cat.id]]
        raised = _raise_to_form_level(core, save, evolved)
        return t(f"{kind}_{how}", n=len(chosen)) + (t("levels_raised", n=raised) if raised else "")

    for kind in ("true", "fourth"):
        if spec.get(kind):
            steps.append((t(f"{kind}_{spec[kind]}", n="").strip(), lambda k=kind: forms(k, spec[k])))

    def talents() -> str:
        chosen, changed = cats(), 0
        if spec["talents"] == "remove":
            for cat in chosen:
                for talent in cat.talents or []:
                    talent.level = 0
                changed += cat.talents is not None
            return t("talents_remove", n=changed)
        data = save.cats.read_talent_data(save)
        if data is None:
            raise RuntimeError(t("no_data"))
        for cat in chosen:
            info = data.get_cat_talents(cat) if cat.talents is not None else None
            if not info:
                continue
            _, max_levels, _, ids = info
            for max_level, talent_id in zip(max_levels, ids):
                talent = cat.get_talent_from_id(talent_id)
                if talent is not None:
                    talent.level = max_level
            changed += 1
        return t("talents_max", n=changed)

    if spec.get("talents"):
        steps.append((t(f"talents_{spec['talents']}", n="").strip(), talents))

    def guide() -> str:
        chosen = cats()
        for cat in chosen:
            cat.catguide_collected = spec["guide"] == "add"
        return t(f"guide_{spec['guide']}", n=len(chosen))

    if spec.get("guide"):
        steps.append((t(f"guide_{spec['guide']}", n="").strip(), guide))
    return steps


def _raise_to_form_level(core: Any, save: Any, cats: list[Any]) -> int:
    """The game glitches when a character has a form its level couldn't have unlocked, so
    raise each newly evolved character to the total (base + plus) level its forms need,
    never lowering it.
    Needs come from unitbuy: 2nd form, true form (or the level-30 true form of the
    starter cats) and ultra form; 30 / 60 when the game data has none (forced forms)."""
    if not cats:
        return 0
    unit_buy = save.cats.read_unitbuy(save)
    raised = 0
    for cat in cats:
        info = unit_buy.get_unit_buy(cat.id) if unit_buy is not None else None
        second = info.second_form_unlock_level if info is not None and info.second_form_unlock_level > 0 else 10
        true = next((v for v in ((info.evolve_level_tf, info.force_true_form_level) if info is not None else ()) if v > 0), 30)
        need = max(second, true)
        if cat.fourth_form:  # only characters that really got the ultra form
            need = max(need, info.evolve_level_ff if info is not None and info.evolve_level_ff > 0 else 60)
        if cat.upgrade.get_base() + cat.upgrade.plus >= need:  # the game counts base + plus levels
            continue
        power_up = core.PowerUpHelper(cat, save)
        if cat.upgrade.get_base() < need:
            power_up.upgrade_by(need - cat.upgrade.get_base())
        short = need - cat.upgrade.get_base() - cat.upgrade.plus
        if short > 0:  # e.g. the starter cats stop at base 20 and reach 30 with plus levels
            cat.upgrade.plus = min(cat.upgrade.plus + short, power_up.get_max_possible_plus())
        raised += 1
    return raised


def _skills(core: Any, save: Any, spec: dict[str, Any]) -> str:
    ability = core.core_data.get_ability_data(save).ability_data
    if not ability:
        raise RuntimeError(t("no_data"))
    valid = save.special_skills.get_valid_skills()
    ids = [i for i in (range(len(valid)) if spec["all"] else spec["ids"]) if i < len(valid) and i < len(ability)]
    if not ids:
        raise RuntimeError(t("nothing"))
    for i in ids:
        max_base, max_plus = ability[i].max_base_level - 1, ability[i].max_plus_level
        base = -1 if spec["base"] is None else (max_base if spec["base"] == "max" else int(spec["base"]) - 1)
        plus = -1 if spec["plus"] is None else (max_plus if spec["plus"] == "max" else int(spec["plus"]))
        save.special_skills.set_upgrade(i, core.Upgrade(plus, base),
                                        max_base=max_base if base != -1 else None,
                                        max_plus=max_plus if plus != -1 else None)
    save.rank_up_sale_value = 0x7FFFFFFF  # like the CLI, so the game doesn't offer a rank-up sale
    level = ("" if spec["base"] is None else str(spec["base"])) + ("" if spec["plus"] is None else f"+{spec['plus']}")
    return t("skills", n=len(ids), level=level.replace("max", "최대" if LANG == "ko" else "max"))


def _ototo(core: Any, save: Any, spec: dict[str, Any]) -> list[Any]:
    steps: list[Any] = []

    def engineers() -> str:
        cap = core.Ototo.get_max_engineers(save)
        save.ototo.engineers = cap if spec["engineers"] == "max" else min(int(spec["engineers"]), cap)
        return t("engineers", n=save.ototo.engineers)

    def cannons() -> str:
        from bcsfe.core.game.gamoto.ototo import CastleRecipeUnlock
        found = save.ototo.cannons
        if found is None or not found.cannons:
            raise RuntimeError(t("nothing"))
        recipe = CastleRecipeUnlock(save)
        for cannon_id, cannon in found.cannons.items():
            cannon.development = max(cannon.development, 3)
            for part_id in range(len(cannon.levels)):
                max_level = recipe.get_max_level(cannon_id, part_id)
                if max_level is not None:
                    cannon.levels[part_id] = max(cannon.levels[part_id], max_level)
        return t("cannons", n=len(found.cannons))

    if spec.get("engineers") is not None:
        steps.append((t("engineers", n="").strip(), engineers))
    if spec.get("max_cannons"):
        steps.append((t("cannons", n="").replace("  ", " ").strip(), cannons))
    return steps


def _gamatoto(core: Any, save: Any, spec: dict[str, Any]) -> list[Any]:
    steps: list[Any] = []
    levels = lambda: core.core_data.get_gamatoto_levels(save)  # noqa: E731

    def level() -> str:
        data = levels()
        max_level = data.get_max_level()
        if not max_level:
            raise RuntimeError(t("no_data"))
        value = max_level if spec["level"] == "max" else max(1, min(int(spec["level"]), max_level))
        xp = data.get_xp_from_level(value)
        if xp is None:
            raise RuntimeError(t("no_data"))
        save.gamatoto.xp = xp
        return t("gamatoto_level", n=value)

    def helpers() -> str:
        from bcsfe.core.game.gamoto.gamatoto import Helper, Helpers
        members = core.core_data.get_gamatoto_members_name(save)
        room = levels().get_total_helpers() or 0
        chosen: list[Any] = []
        for rarity, amount in enumerate(spec["helpers"]):
            pool = members.get_all_rarity(rarity) or []
            for i in range(min(int(amount), room - len(chosen)) if pool else 0):
                chosen.append(Helper(pool[i % len(pool)].member_id))
        save.gamatoto.helpers = Helpers(chosen)
        return t("helpers", n=len(chosen))

    def shrine() -> str:
        data = core.core_data.get_cat_shrine_levels(save)
        max_level = data.get_max_level()
        if not max_level:
            raise RuntimeError(t("no_data"))
        value = max_level if spec["shrine"] == "max" else max(1, min(int(spec["shrine"]), max_level))
        save.cat_shrine.xp_offering = data.get_xp_from_level(value)
        save.cat_shrine.dialogs = value - 1
        return t("shrine", n=value)

    def shrine_show() -> str:
        save.cat_shrine.appear()
        return t("shrine_show")

    if spec.get("level") is not None:
        steps.append((t("gamatoto_level", n="").strip(), level))
    if spec.get("helpers") is not None:
        steps.append((t("helpers", n="").split("(")[0].strip(), helpers))
    if spec.get("shrine") is not None:
        steps.append((t("shrine", n="").strip(), shrine))
    if spec.get("shrine_show"):
        steps.append((t("shrine_show"), shrine_show))
    return steps


def _endless(save: Any, spec: dict[str, Any]) -> str:
    minutes = math.inf if spec["minutes"] == "inf" else float(spec["minutes"])
    items = save.battle_items.items
    ids = [i for i in spec["ids"] if i < len(items)]
    if not ids:
        raise RuntimeError(t("nothing"))
    for i in ids:
        items[i].endless_item.set_duration_mins(minutes, 0)
    time = t("infinite") if spec["minutes"] == "inf" else t("minutes", n=int(minutes))
    return t("endless", n=len(ids), time=time)


def _more_stages(core: Any, save: Any, spec: dict[str, Any]) -> list[Any]:
    def aku_realm() -> str:
        for stage_id in (255, 256, 257, 258, 265, 266, 268):  # the maps the BCSFE CLI clears
            save.event_stages.clear_map(1, stage_id, 0, False)
        return t("aku_realm")

    def aku_chapters() -> str:
        if not save.aku.chapters or not save.aku.chapters[0].chapters:
            raise RuntimeError(t("nothing"))
        stages = save.aku.chapters[0].chapters[0].stages
        for stage in stages:
            stage.clear_stage(max(getattr(stage, "clear_times", 0) or 0, 1))
        return t("aku_chapters", n=len(stages))

    def outbreaks() -> str:
        # A save only lists the zombie stages the game has shown so far (a new account just a few), so add
        # every chapter and stage of the game's full layout first, then clear them all.
        from bcsfe.core.game.map.outbreaks import Chapter as OutbreakChapter, Outbreak
        for chapter_id, stage_ids in _outbreak_layout().items():
            chapter = save.outbreaks.chapters.setdefault(chapter_id, OutbreakChapter(chapter_id, {}))
            for stage_id in stage_ids:
                chapter.outbreaks.setdefault(stage_id, Outbreak(False))
        count = 0
        for chapter in list(save.outbreaks.chapters.values()):
            for stage_id in list(chapter.outbreaks.keys()):
                save.outbreaks.clear_outbreak(chapter.get_true_id(), stage_id, True)
                count += 1
        if not count:
            raise RuntimeError(t("nothing"))
        return t("outbreaks", n=count)

    def filibuster() -> str:
        save.filibuster_stage_enabled = True
        save.filibuster_stage_id = random.randint(0, 47)
        return t("filibuster")

    def challenge() -> str:
        found = save.challenge
        if not found.scores:
            found.scores = [0]
        found.scores[0] = int(spec["score_challenge"])
        found.shown_popup = True
        try:  # like the CLI: mark the challenge stage cleared (skipped if the save has no table for it)
            found.chapters.clear_stage(0, 0, 0, False)
        except IndexError:
            pass
        return t("score_challenge", n=found.scores[0])

    def dojo() -> str:
        save.dojo.chapters.get_stage(0, 0).score = int(spec["score_dojo"])
        return t("score_dojo", n=int(spec["score_dojo"]))

    def itf() -> str:
        for chapter in save.story.get_real_chapters()[3:6]:
            for stage in chapter.get_valid_treasure_stages():
                stage.itf_timed_score = int(spec["score_itf"])
        return t("score_itf", n=int(spec["score_itf"]))

    def tutorial() -> str:
        core.StoryChapters.clear_tutorial(save)
        return t("tutorial")

    table = [("tutorial", tutorial), ("aku_realm", aku_realm), ("aku_chapters", aku_chapters), ("outbreaks", outbreaks),
             ("filibuster", filibuster), ("score_challenge", challenge), ("score_dojo", dojo), ("score_itf", itf)]
    return [(t(k, n="").split("(")[0].strip(), fn) for k, fn in table if spec.get(k) not in (None, False)]


def _progress(core: Any, save: Any, spec: dict[str, Any]) -> list[Any]:
    def slots() -> str:
        lineups = save.lineups
        cap = lineups.slot_names_length or 15
        lineups.unlocked_slots = cap if spec["slots"] == "max" else min(int(spec["slots"]), cap)
        return t("slots", n=lineups.unlocked_slots)

    def playtime() -> str:
        save.officer_pass.play_time = core.PlayTime.from_hours(int(spec["playtime_hours"])).frames
        return t("playtime", n=int(spec["playtime_hours"]))

    def rank_rewards() -> str:
        gifts = core.core_data.get_rank_gifts(save).rank_gift
        if gifts is None:
            raise RuntimeError(t("no_data"))
        rank, rewards, n = save.calculate_user_rank(), save.user_rank_rewards.rewards, 0
        for gift in gifts:
            if gift.index >= len(rewards):
                continue
            reward = rewards[gift.index]
            if spec["rank_rewards"] == "claim" and gift.threshold <= rank and not reward.claimed:
                reward.claimed, n = True, n + 1
            elif spec["rank_rewards"] == "fix" and gift.threshold > rank and reward.claimed:
                reward.claimed, n = False, n + 1
        return t(f"rank_{spec['rank_rewards']}", n=n)

    def medals() -> str:
        names = core.core_data.get_medal_names(save).medal_names
        if names is None:
            raise RuntimeError(t("no_data"))
        add, n = spec["medals"] == "add", 0
        for medal_id, medal in enumerate(names):
            if not medal or save.medals.has_medal(medal_id) == add:
                continue
            (save.medals.add_medal if add else save.medals.remove_medal)(medal_id)
            n += 1
        return t(f"medals_{spec['medals']}", n=n)

    def missions() -> str:
        names = core.core_data.get_mission_names(save).names
        conditions = core.core_data.get_mission_conditions(save)
        if names is None or conditions.conditions is None:
            raise RuntimeError(t("no_data"))
        found, n = save.missions, 0
        state = {"reward": 2, "claimed": 4, "reset": 0}[spec["missions"]]
        for mission_id in names:
            if mission_id not in found.clear_states:
                continue
            condition = conditions.get_condition(mission_id)
            if state and condition is None:
                continue
            found.clear_states[mission_id] = state
            if state:
                found.requirements[mission_id] = condition.progress_count
            elif mission_id in found.requirements:
                found.requirements[mission_id] = 0
            n += 1
        if not n:
            raise RuntimeError(t("nothing"))
        return t(f"missions_{spec['missions']}", n=n)

    def enemy_guide() -> str:
        valid = core.EnemyDictionary(save).get_valid_enemies()
        if valid is None:
            raise RuntimeError(t("no_data"))
        valid = [i for i in valid if i < len(save.enemy_guide)]
        if not valid:
            raise RuntimeError(t("nothing"))
        for enemy_id in valid:
            save.enemy_guide[enemy_id] = 1 if spec["enemy_guide"] == "add" else 0
        return t(f"enemy_{spec['enemy_guide']}", n=len(valid))

    def gold_pass() -> str:
        club = save.officer_pass.gold_pass
        if spec["gold_pass"] == "give":
            club.get_gold_pass(core.NyankoClub.get_random_officer_id(), 30, save)
            return t("gold_give")
        club.remove_gold_pass(save)
        return t("gold_remove")

    def restart_pack() -> str:
        save.restart_pack = 1
        return t("restart_pack")

    def gambling() -> str:
        save.wildcat_slots.reset()
        save.cat_scratcher.reset()
        return t("gambling")

    def golden_cpu() -> str:
        save.golden_cpu_count = 0
        return t("golden_cpu")

    table = [("slots", "slots", slots), ("playtime_hours", "playtime", playtime),
             ("rank_rewards", "rank_claim", rank_rewards), ("medals", "medals_add", medals),
             ("missions", "missions_reward", missions), ("enemy_guide", "enemy_add", enemy_guide),
             ("gold_pass", "gold_give", gold_pass), ("restart_pack", "restart_pack", restart_pack),
             ("reset_gambling", "gambling", gambling), ("reset_golden_cpu", "golden_cpu", golden_cpu)]
    return [(t(label, n="").split(":")[0].strip(), fn) for key, label, fn in table if spec.get(key) not in (None, False)]


def _fix_limits(core: Any, save: Any) -> int:
    """Cap every amount at the game's maximum (and at 0 from below). Over-limit values can crash
    the game or flag the account; premium items are reported like any other change."""
    maxes, changed = core.core_data.max_value_manager, 0
    managed = {"catfood": core.ManagedItemType.CATFOOD, "rare_tickets": core.ManagedItemType.RARE_TICKET,
               "platinum_tickets": core.ManagedItemType.PLATINUM_TICKET, "legend_tickets": core.ManagedItemType.LEGEND_TICKET}
    for attr, cap in (("catfood", maxes.catfood), ("xp", maxes.xp), ("np", maxes.np), ("leadership", maxes.leadership),
                      ("normal_tickets", maxes.normal_tickets), ("rare_tickets", maxes.rare_tickets),
                      ("platinum_tickets", maxes.platinum_tickets), ("legend_tickets", maxes.legend_tickets),
                      ("hundred_million_ticket", maxes.hundred_million_tickets),
                      ("platinum_shards", maxes.platinum_tickets * 10)):
        before = int(getattr(save, attr, 0) or 0)
        after = max(0, min(before, int(cap)))
        if after != before:
            setattr(save, attr, after)
            if attr in managed:
                core.BackupMetaData(save).add_managed_item(core.ManagedItem.from_change(after - before, managed[attr]))
            changed += 1

    def clamp_list(values: list[Any], cap: int, field: str | None = None) -> int:
        n = 0
        for i, v in enumerate(values):
            now = getattr(v, field) if field else v
            fixed = max(0, min(int(now), int(cap)))
            if fixed != now:
                (setattr(v, field, fixed) if field else values.__setitem__(i, fixed))
                n += 1
        return n

    fruit_cap = maxes.catfruit_new if save.game_version >= 110400 else maxes.catfruit_old
    changed += clamp_list(save.battle_items.items, maxes.battle_items, "amount")
    changed += clamp_list(save.catfruit, fruit_cap)
    changed += clamp_list(save.catseyes, maxes.catseyes)
    changed += clamp_list(save.catamins, maxes.catamins)
    changed += clamp_list(save.treasure_chests, maxes.treasure_chests)
    changed += clamp_list(save.labyrinth_medals, maxes.labyrinth_medals)
    changed += clamp_list(save.ototo.base_materials.materials, maxes.base_materials, "amount")
    changed += clamp_list(list(save.talent_orbs.orbs.values()), maxes.talent_orbs, "value")
    return changed


def _fix_levels(core: Any, save: Any) -> int:
    """Bring every owned character's base and plus level within what the game allows for it."""
    unit_buy, changed = save.cats.read_unitbuy(save), 0
    if unit_buy is None:
        raise RuntimeError(t("no_data"))
    for cat in save.cats.get_unlocked_cats():
        info = unit_buy.get_unit_buy(cat.id)
        if info is None:
            continue
        max_base = info.max_upgrade_level_catseye if info.max_upgrade_level_catseye > 0 else None
        max_plus = max(info.max_plus_upgrade_level, 0)
        before = (cat.upgrade.base, cat.upgrade.plus, cat.catseyes_used)
        if cat.upgrade.base < 0:
            cat.upgrade.base = 0
        if max_base is not None and cat.upgrade.get_base() > max_base:
            cat.upgrade.base = max_base - 1
        cat.upgrade.plus = max(0, min(cat.upgrade.plus, max_plus))
        no_eye = info.max_upgrade_level_no_catseye
        cat.catseyes_used = max(0, cat.upgrade.get_base() - no_eye) if no_eye > 0 else 0
        changed += before != (cat.upgrade.base, cat.upgrade.plus, cat.catseyes_used)
    return changed


def _fix_forms(core: Any, save: Any) -> int:
    """Remove true/4th forms a character doesn't have, keep the shown form one it has unlocked,
    and raise levels a form needs (a form the level couldn't reach makes the game glitch)."""
    pic_book, changed, evolved = save.cats.read_nyanko_picture_book(save), 0, []
    for cat in save.cats.get_unlocked_cats():
        book = pic_book.get_cat(cat.id) if pic_book is not None else None
        if book is None:
            continue
        total = book.total_forms
        before = (cat.unlocked_forms, cat.current_form, cat.fourth_form)
        if total < 4 and cat.fourth_form:
            cat.remove_fourth_form()
        if total < 3 and (cat.unlocked_forms or cat.fourth_form):
            cat.remove_true_form()
        highest = 3 if cat.fourth_form else 2 if cat.unlocked_forms >= 3 else min(1, max(total - 1, 0))
        cat.current_form = max(0, min(cat.current_form, highest))
        changed += before != (cat.unlocked_forms, cat.current_form, cat.fourth_form)
        if cat.unlocked_forms or cat.fourth_form:
            evolved.append(cat)
    return changed + _raise_to_form_level(core, save, evolved)


def _fix_lineups(core: Any, save: Any) -> int:
    """Empty lineup slots holding characters the account doesn't own (or twice in one lineup):
    the game can crash when a battle starts with them."""
    cats, emptied = save.cats.cats, 0
    for lineup in save.lineups.slots:
        seen = set()
        for slot in lineup.slots:
            cat_id = slot.cat_id
            if cat_id == -1:
                continue
            if cat_id < 0 or cat_id >= len(cats) or not cats[cat_id].unlocked or cat_id in seen:
                slot.cat_id = -1
                emptied += 1
            else:
                seen.add(cat_id)
    return emptied


REPAIRS = {"fix_limits": _fix_limits, "fix_levels": _fix_levels, "fix_forms": _fix_forms, "fix_lineups": _fix_lineups}


def _fixes(core: Any, save: Any, fixes: list[str]) -> list[Any]:
    def run(fix: str) -> str:
        if fix == "fix_gamatoto":
            save.gamatoto.skin = 2
        elif fix == "fix_ototo":
            save.ototo.cannons = core.game.gamoto.ototo.Cannons.init(save.game_version)
        elif fix == "fix_time":
            now = datetime.datetime.now()
            save.date_3 = now
            save.timestamp = now.timestamp()
            save.energy_penalty_timestamp = now.timestamp()
        elif fix == "fix_equip":
            save.unlock_equip_menu()
        elif fix == "fix_officer":
            save.officer_pass.reset(save)
        elif fix in REPAIRS:
            return t(fix, n=REPAIRS[fix](core, save))
        return t(fix)

    return [(t(fix, n="").replace("  ", " "), lambda f=fix: run(f)) for fix in fixes if fix in FIXES]
