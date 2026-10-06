"""Pronunciation fixes applied to the script text just before text-to-speech.

The TTS phonemiser reads some acronyms as words ("EDR" -> "edder", "APT" -> "apt")
and some names wrongly ("MI5" -> "my five"). This module rewrites the text into
spellings it pronounces correctly. Scripts should be written normally (MFA, EDR,
CISA); never spaced out letter by letter.

Checked against the phonemiser output; extend LEXICON when a new term is misread.
"""
import re

# Exact-token respellings (case-sensitive, whole word).
LEXICON = {
    "CISA": "Sissa",
    "SaaS": "sass",
    "SAAS": "sass",
    "MI5": "M I 5",
    "MI6": "M I 6",
    "DDoS": "dee-doss",
    "2FA": "two-factor",
    "Cl0p": "Clop",
    "Xuanye": "Swan-yay",
    "Kerberos": "Kur-ber-oss",
    "ESXi": "E-S-X-i",
    "vCenter": "v-Center",
    "vSphere": "v-Sphere",
    "PoC": "P-O-C",
    "PoCs": "P-O-Cs",
    "IdP": "I-D-P",
    "OAuth": "oh-auth",
    "LSASS": "ell-sass",
    "Sophos": "Sofoss",
    "Qilin": "Chee-lin",
    "Ivanti": "Ivvanti",
    "ASOS": "Ace-oss",
    "OWASP": "oh-wasp",
    "NIS2": "nis 2",
    "macOS": "mac O-S",
    "iOS": "eye O-S",
}

# Acronyms the phonemiser reads as a word even in context; force letters.
SPELL_HYPHEN = {"EDR", "IOC"}

# All-caps tokens that are genuinely said as words; everything else short and
# all-caps is spelled out letter by letter.
SAY_AS_WORD = {
    "SAML", "NATO", "SOC", "SIEM", "KEV", "NIST", "CERT", "FIPS", "FIDO", "DORA",
    "NASA", "JSON", "YAML", "MITRE", "SCADA", "GIF", "NIS", "LAPSUS", "SOAR",
    "CAPTCHA", "WAF", "SASE", "CASB", "UEFI", "BIOS", "RAM", "ROM", "LAN", "WAN",
    "PIN", "SIM", "NAS", "SAN", "CRUD", "GUI", "AWOL", "OWASP",
}

_spaced_letters = re.compile(r"\b(?:[A-Z] ){1,}[A-Z]\b(?![a-z])")
_caps_token = re.compile(r"\b([A-Z]{2,5})(s?)\b")


def _unspace(m):
    # "M F A" -> "MFA": unspaced capitals are spelled out cleanly in context,
    # whereas spaced or hyphenated letters turn a final "A" into "uh".
    return m.group(0).replace(" ", "")


def _caps(m):
    word, plural = m.group(1), m.group(2)
    if word in SAY_AS_WORD:
        return word.lower() + plural  # lowercase so it's read as a word
    if word in SPELL_HYPHEN:
        return "-".join(word) + plural
    return m.group(0)  # the phonemiser spells other capitals correctly in context


def fix(text: str) -> str:
    # 1. undo letter-spacing ("M F A" -> "M-F-A"); a lone "A"/"I" is left alone
    text = _spaced_letters.sub(_unspace, text)
    # 2. lexicon respellings
    for k, v in LEXICON.items():
        text = re.sub(rf"(?<![\w-]){re.escape(k)}(?![\w-])", v, text)
    # 3. word-acronyms lowercased (SOC -> soc); known troublemakers hyphenated
    text = _caps_token.sub(_caps, text)
    return text


if __name__ == "__main__":
    import sys
    print(fix(sys.stdin.read()))
