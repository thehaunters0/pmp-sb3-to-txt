#!/usr/bin/env python3
"""
pmp_to_txt.py - turn a PenguinMod (.pmp) or Scratch 3 (.sb3) project into a readable text file.

A .pmp is a zip archive holding project.json (same block format as Scratch's .sb3).
This reads that JSON and prints every script of every sprite as plain text:

    === Sprite: Cat ===
    When green flag clicked
    Forever
      Move 10 steps
      If <touching (edge)?> then
        Turn right 15 degrees
      End
    End

Usage:
    python pmp_to_txt.py project.pmp              -> writes project.txt next to it
    python pmp_to_txt.py project.pmp -o out.txt   -> choose the output file
    python pmp_to_txt.py project.pmp --stdout     -> print instead of writing
    python pmp_to_txt.py                          -> opens a file picker

Notation: (round) = reporter / number slot, <pointy> = true/false slot,
[square] = dropdown, variable or list name. Extension blocks and anything not in
the built-in table below are still printed, in the form  "ext: block name [INPUT=value]".
Needs only Python 3.7+ (no extra packages).
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile

# --------------------------------------------------------------------------
# Block text templates.  {NAME} is replaced by the input/field called NAME.
# Reporters carry their own ( ) or < > brackets.
# --------------------------------------------------------------------------
T = {
    # motion
    "motion_movesteps": "move {STEPS} steps",
    "motion_turnright": "turn right {DEGREES} degrees",
    "motion_turnleft": "turn left {DEGREES} degrees",
    "motion_goto": "go to {TO}",
    "motion_gotoxy": "go to x: {X} y: {Y}",
    "motion_glideto": "glide {SECS} secs to {TO}",
    "motion_glidesecstoxy": "glide {SECS} secs to x: {X} y: {Y}",
    "motion_pointindirection": "point in direction {DIRECTION}",
    "motion_pointtowards": "point towards {TOWARDS}",
    "motion_changexby": "change x by {DX}",
    "motion_setx": "set x to {X}",
    "motion_changeyby": "change y by {DY}",
    "motion_sety": "set y to {Y}",
    "motion_ifonedgebounce": "if on edge, bounce",
    "motion_setrotationstyle": "set rotation style [{STYLE}]",
    "motion_xposition": "(x position)",
    "motion_yposition": "(y position)",
    "motion_direction": "(direction)",
    # looks
    "looks_sayforsecs": "say {MESSAGE} for {SECS} seconds",
    "looks_say": "say {MESSAGE}",
    "looks_thinkforsecs": "think {MESSAGE} for {SECS} seconds",
    "looks_think": "think {MESSAGE}",
    "looks_switchcostumeto": "switch costume to {COSTUME}",
    "looks_nextcostume": "next costume",
    "looks_switchbackdropto": "switch backdrop to {BACKDROP}",
    "looks_nextbackdrop": "next backdrop",
    "looks_changesizeby": "change size by {CHANGE}",
    "looks_setsizeto": "set size to {SIZE} %",
    "looks_changeeffectby": "change [{EFFECT}] effect by {CHANGE}",
    "looks_seteffectto": "set [{EFFECT}] effect to {VALUE}",
    "looks_cleargraphiceffects": "clear graphic effects",
    "looks_show": "show",
    "looks_hide": "hide",
    "looks_gotofrontback": "go to [{FRONT_BACK}] layer",
    "looks_goforwardbackwardlayers": "go [{FORWARD_BACKWARD}] {NUM} layers",
    "looks_costumenumbername": "(costume [{NUMBER_NAME}])",
    "looks_backdropnumbername": "(backdrop [{NUMBER_NAME}])",
    "looks_size": "(size)",
    # sound
    "sound_playuntildone": "play sound {SOUND_MENU} until done",
    "sound_play": "start sound {SOUND_MENU}",
    "sound_stopallsounds": "stop all sounds",
    "sound_changeeffectby": "change [{EFFECT}] sound effect by {VALUE}",
    "sound_seteffectto": "set [{EFFECT}] sound effect to {VALUE}",
    "sound_cleareffects": "clear sound effects",
    "sound_changevolumeby": "change volume by {VOLUME}",
    "sound_setvolumeto": "set volume to {VOLUME} %",
    "sound_volume": "(volume)",
    # events
    "event_whenflagclicked": "when green flag clicked",
    "event_whenkeypressed": "when [{KEY_OPTION}] key pressed",
    "event_whenthisspriteclicked": "when this sprite clicked",
    "event_whenstageclicked": "when stage clicked",
    "event_whenbackdropswitchesto": "when backdrop switches to [{BACKDROP}]",
    "event_whengreaterthan": "when [{WHENGREATERTHANMENU}] > {VALUE}",
    "event_whenbroadcastreceived": "when I receive [{BROADCAST_OPTION}]",
    "event_broadcast": "broadcast {BROADCAST_INPUT}",
    "event_broadcastandwait": "broadcast {BROADCAST_INPUT} and wait",
    # control
    "control_wait": "wait {DURATION} seconds",
    "control_repeat": "repeat {TIMES}",
    "control_forever": "forever",
    "control_if": "if {CONDITION} then",
    "control_if_else": "if {CONDITION} then",
    "control_wait_until": "wait until {CONDITION}",
    "control_repeat_until": "repeat until {CONDITION}",
    "control_while": "while {CONDITION}",
    "control_for_each": "for each [{VARIABLE}] in {VALUE}",
    "control_stop": "stop [{STOP_OPTION}]",
    "control_start_as_clone": "when I start as a clone",
    "control_create_clone_of": "create clone of {CLONE_OPTION}",
    "control_delete_this_clone": "delete this clone",
    "control_all_at_once": "all at once",
    # sensing
    "sensing_touchingobject": "<touching {TOUCHINGOBJECTMENU}?>",
    "sensing_touchingcolor": "<touching color {COLOR}?>",
    "sensing_coloristouchingcolor": "<color {COLOR} is touching {COLOR2}?>",
    "sensing_distanceto": "(distance to {DISTANCETOMENU})",
    "sensing_askandwait": "ask {QUESTION} and wait",
    "sensing_answer": "(answer)",
    "sensing_keypressed": "<key {KEY_OPTION} pressed?>",
    "sensing_mousedown": "<mouse down?>",
    "sensing_mousex": "(mouse x)",
    "sensing_mousey": "(mouse y)",
    "sensing_setdragmode": "set drag mode [{DRAG_MODE}]",
    "sensing_loudness": "(loudness)",
    "sensing_timer": "(timer)",
    "sensing_resettimer": "reset timer",
    "sensing_of": "([{PROPERTY}] of {OBJECT})",
    "sensing_current": "(current [{CURRENTMENU}])",
    "sensing_dayssince2000": "(days since 2000)",
    "sensing_username": "(username)",
    # operators
    "operator_add": "({NUM1} + {NUM2})",
    "operator_subtract": "({NUM1} - {NUM2})",
    "operator_multiply": "({NUM1} * {NUM2})",
    "operator_divide": "({NUM1} / {NUM2})",
    "operator_random": "(pick random {FROM} to {TO})",
    "operator_gt": "<{OPERAND1} > {OPERAND2}>",
    "operator_lt": "<{OPERAND1} < {OPERAND2}>",
    "operator_equals": "<{OPERAND1} = {OPERAND2}>",
    "operator_and": "<{OPERAND1} and {OPERAND2}>",
    "operator_or": "<{OPERAND1} or {OPERAND2}>",
    "operator_not": "<not {OPERAND}>",
    "operator_join": "(join {STRING1} {STRING2})",
    "operator_letter_of": "(letter {LETTER} of {STRING})",
    "operator_length": "(length of {STRING})",
    "operator_contains": "<{STRING1} contains {STRING2}?>",
    "operator_mod": "({NUM1} mod {NUM2})",
    "operator_round": "(round {NUM})",
    "operator_mathop": "([{OPERATOR}] of {NUM})",
    # variables / lists
    "data_variable": "({VARIABLE})",
    "data_listcontents": "({LIST})",
    "data_setvariableto": "set [{VARIABLE}] to {VALUE}",
    "data_changevariableby": "change [{VARIABLE}] by {VALUE}",
    "data_showvariable": "show variable [{VARIABLE}]",
    "data_hidevariable": "hide variable [{VARIABLE}]",
    "data_addtolist": "add {ITEM} to [{LIST}]",
    "data_deleteoflist": "delete {INDEX} of [{LIST}]",
    "data_deletealloflist": "delete all of [{LIST}]",
    "data_insertatlist": "insert {ITEM} at {INDEX} of [{LIST}]",
    "data_replaceitemoflist": "replace item {INDEX} of [{LIST}] with {ITEM}",
    "data_itemoflist": "(item {INDEX} of [{LIST}])",
    "data_itemnumoflist": "(item # of {ITEM} in [{LIST}])",
    "data_lengthoflist": "(length of [{LIST}])",
    "data_listcontainsitem": "<[{LIST}] contains {ITEM}?>",
    "data_showlist": "show list [{LIST}]",
    "data_hidelist": "hide list [{LIST}]",
    # PenguinMod extras
    "operator_notequal": "<{OPERAND1} != {OPERAND2}>",
    "sensing_mouseclicked": "<mouse clicked?>",
    "data_amountinlist": "(amount of {VALUE} in [{LIST}])",
    "pmOperatorsExpansion_ifIsTruthy": "(if {ONE} is truthy then {TWO})",
    "pmOperatorsExpansion_orIfFalsey": "({ONE} or if falsey {TWO})",
    # custom block arguments
    "argument_reporter_string_number": "({VALUE})",
    "argument_reporter_boolean": "<{VALUE}>",
    # pen extension
    "pen_clear": "erase all",
    "pen_stamp": "stamp",
    "pen_penDown": "pen down",
    "pen_penUp": "pen up",
    "pen_setPenColorToColor": "set pen color to {COLOR}",
    "pen_changePenColorParamBy": "change pen [{COLOR_PARAM}] by {VALUE}",
    "pen_setPenColorParamTo": "set pen [{COLOR_PARAM}] to {VALUE}",
    "pen_changePenSizeBy": "change pen size by {SIZE}",
    "pen_setPenSizeTo": "set pen size to {SIZE}",
}

HAT_PREFIXES = ("event_when", "control_start_as_clone")
C_BLOCKS = {
    "control_repeat", "control_forever", "control_if", "control_if_else",
    "control_repeat_until", "control_while", "control_for_each", "control_all_at_once",
}


def jlist(x):
    """Mutation values are often JSON strings like '["a","b"]'."""
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            v = json.loads(x)
            return v if isinstance(v, list) else []
        except ValueError:
            return []
    return []


def nat(key):
    """Order branch keys: SUBSTACK, SUBSTACK2, SUBSTACK3 ... with ELSE last."""
    if re.match(r"ELSE", key, re.I):
        return 9999
    m = re.search(r"(\d+)$", key)
    return int(m.group(1)) if m else 1


# --------------------------------------------------------------------------
# Extensions: read the block text out of the extension's own JavaScript so that
# extension blocks print like  "print text (hello) with ID (my-text)".
# --------------------------------------------------------------------------
def parse_ext_code(extid, code, templates, c_blocks):
    ops = list(re.finditer(r"opcode\s*:\s*[\"'](\w+)[\"']", code))
    for n, m in enumerate(ops):
        end = ops[n + 1].start() if n + 1 < len(ops) else len(code)
        seg = code[m.end():end]
        tm = re.search(r"\btext\s*:\s*(?:Scratch\.translate\(\s*)?([\"'`])(.*?)\1", seg, re.S)
        if not tm:
            continue
        bt = re.search(r"BlockType\.(\w+)", seg) or re.search(r"BlockType\.(\w+)", code[max(0, m.start() - 120):m.start()])
        btype = bt.group(1) if bt else "COMMAND"
        tpl = re.sub(r"\[(\w+)\]", r"{\1}", tm.group(2))
        if btype == "REPORTER":
            tpl = "(" + tpl + ")"
        elif btype == "BOOLEAN":
            tpl = "<" + tpl + ">"
        key = extid + "_" + m.group(1)
        templates[key] = tpl
        if btype in ("LOOP", "CONDITIONAL"):
            c_blocks.add(key)


def load_extensions(project, fetch=False):
    """Returns (templates, c_blocks, description lines)."""
    templates, c_blocks, lines = {}, set(), []
    exts = project.get("extensions") or []
    urls = project.get("extensionURLs") or {}
    if exts or urls:
        lines.append("Extensions used: " + (", ".join(map(str, exts)) or "(none listed)"))
    for extid, url in urls.items():
        code, note = None, str(url)
        if isinstance(url, str) and url.startswith("data:"):
            head, _, body = url.partition(",")
            try:
                code = (base64.b64decode(body).decode("utf-8", "replace") if ";base64" in head
                        else urllib.parse.unquote(body))
            except Exception:
                code = None
            meta = dict(re.findall(r"^//\s*(Name|By|Version):\s*(.+?)\s*$", code or "", re.M))
            note = "embedded in the project" + (
                " (" + ", ".join("%s: %s" % kv for kv in meta.items()) + ")" if meta else "")
        elif fetch and isinstance(url, str) and url.startswith("http"):
            try:
                with urllib.request.urlopen(url, timeout=15) as r:
                    code = r.read().decode("utf-8", "replace")
            except Exception as e:
                note += "  (could not download: %s)" % e
        if code:
            parse_ext_code(extid, code, templates, c_blocks)
        lines.append("  custom extension %s: %s" % (extid, note))
    return templates, c_blocks, lines


class Renderer:
    def __init__(self, blocks, ext_templates=None, ext_c_blocks=None,
                 comments=None, show_comments=True):
        self.blocks = blocks
        self.ext = ext_templates or {}
        self.ext_c = ext_c_blocks or set()
        self.comments = comments or {}
        self.show_comments = show_comments
        self.shown = set()          # ids of comments already printed next to their block

    def add_comment(self, b, depth, out):
        """Print the comment attached to block b (if any) right under its line."""
        cid = b.get("comment")
        c = self.comments.get(cid) if cid else None
        if not c or not self.show_comments:
            return
        self.shown.add(cid)
        for line in str(c.get("text", "")).splitlines() or [""]:
            out.append("  " * depth + "// " + line)

    def tpl(self, op):
        return T.get(op) or self.ext.get(op)

    # ---- values -------------------------------------------------------
    def input_text(self, inp):
        if not isinstance(inp, list) or len(inp) < 2:
            return ""
        v = inp[1]
        if v is None and len(inp) > 2:
            v = inp[2]
        return self.value(v)

    def value(self, v):
        if v is None:
            return ""
        if isinstance(v, list):
            return self.primitive(v)
        if isinstance(v, str):
            return self.reporter(v)
        return str(v)

    @staticmethod
    def primitive(p):
        if not p:
            return ""
        t = p[0]
        val = p[1] if len(p) > 1 else ""
        if t in (12, 13):          # variable / list reporter
            return "(%s)" % val
        return "" if val is None else str(val)

    def reporter(self, bid):
        b = self.blocks.get(bid)
        if b is None:
            return ""
        if isinstance(b, list):
            return self.primitive(b)
        fields, inputs = b.get("fields", {}), b.get("inputs", {})
        # dropdown menu blocks (shadows) -> just the chosen value
        if b.get("shadow") and fields and not inputs:
            return self.field_text(next(iter(fields.values())))
        return self.header(b, as_reporter=True)

    @staticmethod
    def field_text(f):
        if isinstance(f, list):
            return "" if not f or f[0] is None else str(f[0])
        return str(f)

    def lookup(self, b, name):
        inputs, fields = b.get("inputs", {}), b.get("fields", {})
        if name in inputs:
            return self.input_text(inputs[name])
        if name in fields:
            return self.field_text(fields[name])
        return ""

    # ---- which inputs are "stacks" (bodies of C-blocks)? ---------------
    def is_statement(self, bid):
        b = self.blocks.get(bid)
        if not isinstance(b, dict) or b.get("shadow"):
            return False
        op = b.get("opcode", "")
        t = self.tpl(op)
        if t is not None:
            return t[:1] not in "(<"
        if op == "procedures_call":
            return not str((b.get("mutation") or {}).get("return", "")).lower() in ("true", "1")
        return True

    def stack_keys(self, b):
        op = b.get("opcode", "")
        t = self.tpl(op) or ""
        used = set(re.findall(r"\{(\w+)\}", t))
        keys = []
        for k, inp in b.get("inputs", {}).items():
            if k in used or not (isinstance(inp, list) and len(inp) > 1 and isinstance(inp[1], str)):
                continue
            if re.match(r"(SUBSTACK|ELSE|BRANCH)\d*$", k, re.I):
                keys.append(k)
            elif (inp[0] == 2 and not re.match(r"(BOOL|COND|OPERAND|ARG)", k, re.I)
                  and self.is_statement(inp[1])):
                keys.append(k)
        return sorted(keys, key=nat)

    # ---- one block's own line -----------------------------------------
    def header(self, b, as_reporter=False, skip=()):
        op = b.get("opcode", "")
        mut = b.get("mutation") or {}

        if op == "procedures_call":
            ids = jlist(mut.get("argumentids"))
            vals = iter([self.input_text(b.get("inputs", {}).get(i)) for i in ids])
            text = re.sub(r"%[sbn]", lambda m: next(vals, ""), mut.get("proccode", "custom block"))
            return "(%s)" % text if as_reporter else text

        if op == "procedures_definition":
            proto = self.blocks.get((b.get("inputs", {}).get("custom_block") or [None, None])[1]) or {}
            pm = proto.get("mutation") or {}
            names = iter(jlist(pm.get("argumentnames")))
            def arg(m):
                n = next(names, "arg")
                return "<%s>" % n if m.group(0) == "%b" else "(%s)" % n
            return "define " + re.sub(r"%[sbn]", arg, pm.get("proccode", "custom block"))

        t = self.tpl(op)
        if t is not None:
            return re.sub(r"\{(\w+)\}", lambda m: self.lookup(b, m.group(1)), t)

        # ---- fallback for blocks we have no text for ----
        ext, _, name = op.partition("_")
        if not name:
            ext, name = "", op
        words = re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("_", " ").lower()
        args = []
        for k, v in b.get("inputs", {}).items():
            if k in skip or k.startswith("SUBSTACK"):
                continue
            args.append("%s=%s" % (k, self.input_text(v)))
        for k, v in b.get("fields", {}).items():
            args.append("%s=%s" % (k, self.field_text(v)))
        text = (ext + ": " if ext else "") + words
        if args:
            text += " [" + ", ".join(args) + "]"
        return "(%s)" % text if as_reporter else text

    # ---- stacks -------------------------------------------------------
    def stack(self, bid, depth, out):
        seen = set()
        while bid and bid not in seen:
            seen.add(bid)
            b = self.blocks.get(bid)
            if isinstance(b, list):          # loose variable reporter
                out.append("  " * depth + self.primitive(b))
                break
            if not isinstance(b, dict):
                break
            self.statement(b, depth, out)
            bid = b.get("next")

    def statement(self, b, depth, out):
        pad = "  " * depth
        op = b.get("opcode", "")
        inputs = b.get("inputs", {})

        # PenguinMod's expandable "if / else if / else" block
        if re.search(r"expandable_?if|if_?expandable", op, re.I):
            self.expandable_if(b, depth, out)
            return

        keys = self.stack_keys(b)
        text = self.header(b, skip=keys)
        out.append(pad + (text[:1].upper() + text[1:]))
        self.add_comment(b, depth, out)

        is_c = op in C_BLOCKS or op in self.ext_c or keys
        if not is_c:
            return
        if op == "control_if_else" or (op in C_BLOCKS and "SUBSTACK2" in inputs):
            self.stack(self.sub(inputs.get("SUBSTACK")), depth + 1, out)
            out.append(pad + "Else")
            self.stack(self.sub(inputs.get("SUBSTACK2")), depth + 1, out)
        elif len(keys) <= 1:
            self.stack(self.sub(inputs.get(keys[0] if keys else "SUBSTACK")), depth + 1, out)
        else:                                   # several unlabeled bodies: show the key names
            for k in keys:
                out.append(pad + "  [" + k + "]")
                self.stack(self.sub(inputs.get(k)), depth + 2, out)
        out.append(pad + "End")

    def expandable_if(self, b, depth, out):
        pad = "  " * depth
        inputs = b.get("inputs", {})
        conds = sorted([k for k in inputs if re.match(r"(BOOL|COND(ITION)?)\d*$", k, re.I)], key=nat)
        bodies = self.stack_keys(b)
        else_key = next((k for k in bodies if re.match(r"ELSE", k, re.I)), None)
        if else_key:
            bodies.remove(else_key)
        elif len(bodies) > len(conds):
            else_key = bodies.pop()
        for i, ck in enumerate(conds):
            head = ("If " if i == 0 else "Else if ") + self.input_text(inputs.get(ck)) + " then"
            out.append(pad + head)
            if i == 0:
                self.add_comment(b, depth, out)
            if i < len(bodies):
                self.stack(self.sub(inputs.get(bodies[i])), depth + 1, out)
        if else_key:
            out.append(pad + "Else")
            self.stack(self.sub(inputs.get(else_key)), depth + 1, out)
        out.append(pad + "End")

    @staticmethod
    def sub(inp):
        return inp[1] if isinstance(inp, list) and len(inp) > 1 and isinstance(inp[1], str) else None


# --------------------------------------------------------------------------
def load_project(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.split("/")[-1] == "project.json"]
            if not names:
                raise SystemExit("No project.json inside that file - is it really a .pmp / .sb3?")
            return json.loads(z.read(names[0]).decode("utf-8"))
    with open(path, "r", encoding="utf-8") as f:     # plain JSON project
        return json.load(f)


def convert(project, fetch=False, comments=True):
    out = []
    templates, ext_c, lines = load_extensions(project, fetch)
    if lines:
        out.extend(lines)
        out.append("")

    for target in project.get("targets", []):
        name = "Stage" if target.get("isStage") else "Sprite: " + str(target.get("name", "?"))
        out.append("=" * 8 + " " + name + " " + "=" * 8)

        vs = [v[0] for v in (target.get("variables") or {}).values()]
        ls = [v[0] for v in (target.get("lists") or {}).values()]
        if vs:
            out.append("Variables: " + ", ".join(map(str, vs)))
        if ls:
            out.append("Lists: " + ", ".join(map(str, ls)))

        blocks = target.get("blocks") or {}
        r = Renderer(blocks, templates, ext_c, target.get("comments") or {}, comments)
        tops = [(k, b) for k, b in blocks.items()
                if (isinstance(b, dict) and b.get("topLevel") and not b.get("shadow")) or isinstance(b, list)]
        tops.sort(key=lambda kb: (
            (kb[1].get("y", 0), kb[1].get("x", 0)) if isinstance(kb[1], dict)
            else (kb[1][4] if len(kb[1]) > 4 else 0, kb[1][3] if len(kb[1]) > 3 else 0)))
        if not tops:
            out.append("(no scripts)")
        for i, (bid, _) in enumerate(tops, 1):
            out.append("")
            out.append("--- Script %d ---" % i)
            r.stack(bid, 0, out)
        if comments:
            cs = target.get("comments") or {}
            free = sorted((c for c in cs.values() if isinstance(c, dict) and not c.get("blockId")),
                          key=lambda c: (c.get("y", 0), c.get("x", 0)))
            left = [(cid, c) for cid, c in cs.items()
                    if isinstance(c, dict) and c.get("blockId") and cid not in r.shown]
            if free or left:
                out.append("")
                out.append("--- Comments ---")
                for c in free:
                    out.extend("// " + l for l in (str(c.get("text", "")).splitlines() or [""]))
                    out.append("")
                for cid, c in left:
                    blk = blocks.get(c.get("blockId"))
                    where = r.header(blk) if isinstance(blk, dict) else "a block"
                    out.append("(on: %s)" % where)
                    out.extend("// " + l for l in (str(c.get("text", "")).splitlines() or [""]))
                    out.append("")
        out.append("")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def pick_file():
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        return filedialog.askopenfilename(
            title="Choose a PenguinMod project",
            filetypes=[("PenguinMod / Scratch projects", "*.pmp *.sb3 *.json"), ("All files", "*.*")])
    except Exception:
        return input("Path to your .pmp file: ").strip().strip('"')


def main():
    ap = argparse.ArgumentParser(description="Convert a PenguinMod .pmp project to a text file.")
    ap.add_argument("file", nargs="?", help="the .pmp (or .sb3) file")
    ap.add_argument("-o", "--output", help="output .txt path")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing a file")
    ap.add_argument("--no-comments", action="store_true",
                    help="leave out block and workspace comments")
    ap.add_argument("--fetch", action="store_true",
                    help="download extensions that are loaded from a URL so their blocks get readable names")
    a = ap.parse_args()

    path = a.file or pick_file()
    if not path:
        return
    text = convert(load_project(path), a.fetch, not a.no_comments)
    if a.stdout:
        sys.stdout.write(text)
        return
    out_path = a.output or os.path.splitext(path)[0] + ".txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
