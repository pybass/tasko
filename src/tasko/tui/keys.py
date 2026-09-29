"""Key binding helpers."""

from dataclasses import replace
from typing import Final

from textual.binding import Binding, BindingType

# Russian ЙЦУКЕН: what each Latin key types. The terminal sends characters, not physical keys, so
# a binding stays dead while the Russian layout is on unless it names this twin too. The `?` key
# types `,` in the macOS "Russian - PC" layout; `+`, `=`, `-` type themselves there and in "Russian".
_RU_LAYOUT: Final = dict(zip("qwertyuiopasdfghjklzxcvbnm", "йцукенгшщзфывапролдячсмить", strict=True)) | {
    "question_mark": "comma"
}


def with_ru_layout(bindings: list[BindingType]) -> list[BindingType]:
    """Bind every key to its Russian-layout twin as well: `k` also fires on `л`, `A` on `Ф`, `ctrl+a` on `ctrl+ф`, `?` on `,`."""
    result: list[BindingType] = []
    for binding in bindings:
        b = binding if isinstance(binding, Binding) else Binding(*binding)
        keys = [key.strip() for key in b.key.split(",")]
        twins = []
        for key in keys:
            modifiers, plus, char = key.rpartition("+")
            if (twin := _RU_LAYOUT.get(char.lower())) is not None:
                twins.append(f"{modifiers}{plus}{twin.upper() if char.isupper() else twin}")
        result.append(replace(b, key=",".join([*keys, *twins])))
    return result
