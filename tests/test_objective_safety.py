"""Syntax-only objective regressions. Synthetic malformed/ambiguous inputs are labeled."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.objective_ref import objective_reference, match_bracket, bracket_name_for, UNKNOWN

# Synthetic denial: a verb in the target name does not authorize movement.
for text in ['You must not approach <a href=showinfo:1//2>Cloud</a>',
             'You need to destroy <a href=showinfo:1//2>Approach beacon</a>']:
    ref = objective_reference(text)
    assert ref is not None and ref['verb'] == UNKNOWN, text
print('[PASS] ungrounded or negated instruction never grants movement')

# Quoted URL appears in HTML; preserve precise identity, not floats.
r = objective_reference('You need to approach <a href="showinfo:10131//9002321446000117567">Fire Cloud</a>')
assert r is not None and r['item_id'] == 9002321446000117567, r
print('[PASS] quoted objective anchor preserves exact integer ID')
for malformed in ['showinfo:1 //2', 'showinfo:1// 2', 'showinfo:1//2oops']:
    r = objective_reference(f'You need to approach <a href={malformed}>Cloud</a>')
    assert r is not None and r['item_id'] is None, r
print('[PASS] malformed ID tokens are not repaired')
rows = [{'name':'__inflightbracket_2','label':'Cloud','center':(10,20)}]
assert match_bracket(rows,1,'Cloud') is None
assert match_bracket(rows+rows,2) is None
assert match_bracket([{'name':'__inflightbracket_2_extra','center':(1,2)}],2) is None
assert bracket_name_for(' 2') is None
print('[PASS] duplicate, mismatched and suffix bracket identities are rejected')
