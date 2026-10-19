from minutemate.text.normalize import normalize


def test_half_space_for_present_verb():
    assert normalize("می روم") == "می\u200cروم"


def test_glossary_term_replacement():
    assert normalize("دیتا بیس پروژه") == "دیتابیس پروژه"


def test_plural_half_space():
    assert normalize("کتاب ها") == "کتاب\u200cها"


def test_whitespace_collapse():
    assert normalize("سلام    دنیا") == "سلام دنیا"
