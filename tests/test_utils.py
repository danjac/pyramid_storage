# -*- coding: utf-8 -*-


def test_secure_filename():
    from pyramid_storage.utils import secure_filename

    assert secure_filename("My cool movie.mov") == "My_cool_movie.mov"
    assert secure_filename("../../../etc/passwd") == "etc_passwd"

    target = "i_contain_cool_umlauts.txt"

    assert secure_filename("i contain cool \xfcml\xe4uts.txt") == target


def test_random_filename():
    from pyramid_storage.utils import random_filename

    filename = random_filename("my little pony.png")
    assert filename.endswith(".png")
    assert filename != "my little pony.png"
