from package.utils.functions import fetch_str


class Test:
    name: str

    def __str__(self) -> str:
        return self.name


class StrTest:
    name: str

    def __str__(self) -> str:
        return str(self.name)


def test_str():
    """
    Ensures `fetch_str` works for both `str(self.x)` and `self.x`
    """
    assert fetch_str(Test) == "name"
    assert fetch_str(StrTest) == "name"
