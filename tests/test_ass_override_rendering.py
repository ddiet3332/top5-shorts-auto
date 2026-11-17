"""Regression for run #121: ASS overrides must not appear as literal text."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_auto_v29 import cue_with_ass_override


def test_ass_override_is_actual_tag_not_escaped_text():
    line=cue_with_ass_override(0,4,"Active","▶ 3위",35,700,7,6,r"{\\fs92\\bord7}")
    assert r"{\\fs92\\bord7}▶ 3위" in line
    assert r"\\{\\\\fs92" not in line
    assert line.count("Dialogue:")==1


def test_ass_header_override_is_actual_tag():
    line=cue_with_ass_override(0,27,"MainTopic","강아지 TOP5",540,112,8,5,r"{\\fs82\\bord3}")
    assert r"{\\fs82\\bord3}강아지 TOP5" in line
