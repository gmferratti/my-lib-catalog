import pytest

from catalog.scanning import normalizar_isbn


def test_isbn13_valido():
    assert normalizar_isbn("9781098115784") == "9781098115784"


def test_isbn10_valido():
    assert normalizar_isbn("0306406152") == "0306406152"


def test_strips_hifens():
    assert normalizar_isbn("978-1098115784") == "9781098115784"


def test_isbn10_com_x():
    assert normalizar_isbn("155860832X") == "155860832X"


def test_isbn10_com_x_minusculo():
    assert normalizar_isbn("155860832x") == "155860832X"


def test_muito_curto():
    assert normalizar_isbn("123") is None


def test_muito_longo():
    assert normalizar_isbn("12345678901234") is None


def test_string_vazia():
    assert normalizar_isbn("") is None


def test_11_digitos():
    assert normalizar_isbn("12345678901") is None


def test_strips_espacos():
    assert normalizar_isbn("978 1098 115784") == "9781098115784"
