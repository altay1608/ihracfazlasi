L_PATTERNS = {
    "0": "0001101",
    "1": "0011001",
    "2": "0010011",
    "3": "0111101",
    "4": "0100011",
    "5": "0110001",
    "6": "0101111",
    "7": "0111011",
    "8": "0110111",
    "9": "0001011",
}

G_PATTERNS = {
    "0": "0100111",
    "1": "0110011",
    "2": "0011011",
    "3": "0100001",
    "4": "0011101",
    "5": "0111001",
    "6": "0000101",
    "7": "0010001",
    "8": "0001001",
    "9": "0010111",
}

R_PATTERNS = {
    "0": "1110010",
    "1": "1100110",
    "2": "1101100",
    "3": "1000010",
    "4": "1011100",
    "5": "1001110",
    "6": "1010000",
    "7": "1000100",
    "8": "1001000",
    "9": "1110100",
}

PARITY_PATTERNS = {
    "0": "LLLLLL",
    "1": "LLGLGG",
    "2": "LLGGLG",
    "3": "LLGGGL",
    "4": "LGLLGG",
    "5": "LGGLLG",
    "6": "LGGGLL",
    "7": "LGLGLG",
    "8": "LGLGGL",
    "9": "LGGLGL",
}

CODE39_PATTERNS = {
    "0": "nnnwwnwnn",
    "1": "wnnwnnnnw",
    "2": "nnwwnnnnw",
    "3": "wnwwnnnnn",
    "4": "nnnwwnnnw",
    "5": "wnnwwnnnn",
    "6": "nnwwwnnnn",
    "7": "nnnwnnwnw",
    "8": "wnnwnnwnn",
    "9": "nnwwnnwnn",
    "A": "wnnnnwnnw",
    "B": "nnwnnwnnw",
    "C": "wnwnnwnnn",
    "D": "nnnnwwnnw",
    "E": "wnnnwwnnn",
    "F": "nnwnwwnnn",
    "G": "nnnnnwwnw",
    "H": "wnnnnwwnn",
    "I": "nnwnnwwnn",
    "J": "nnnnwwwnn",
    "K": "wnnnnnnww",
    "L": "nnwnnnnww",
    "M": "wnwnnnnwn",
    "N": "nnnnwnnww",
    "O": "wnnnwnnwn",
    "P": "nnwnwnnwn",
    "Q": "nnnnnnwww",
    "R": "wnnnnnwwn",
    "S": "nnwnnnwwn",
    "T": "nnnnwnwwn",
    "U": "wwnnnnnnw",
    "V": "nwwnnnnnw",
    "W": "wwwnnnnnn",
    "X": "nwnnwnnnw",
    "Y": "wwnnwnnnn",
    "Z": "nwwnwnnnn",
    "-": "nwnnnnwnw",
    ".": "wwnnnnwnn",
    " ": "nwwnnnwnn",
    "$": "nwnwnwnnn",
    "/": "nwnwnnnwn",
    "+": "nwnnnwnwn",
    "%": "nnnwnwnwn",
    "*": "nwnnwnwnn",
}


CODE128_PATTERNS = (
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
)


def get_compact_barcode_payload(barcode):
    raw_value = str(barcode or "").strip().upper()
    if not raw_value:
        return ""

    if "-" in raw_value:
        base_part = raw_value.split("-", 1)[0].strip()
        if base_part.isdigit() and len(base_part) == 12:
            return append_ean13_check_digit(base_part)

    digits_only = "".join(char for char in raw_value if char.isdigit())
    if digits_only.isdigit() and len(digits_only) == 12:
        return append_ean13_check_digit(digits_only)
    if digits_only.isdigit() and len(digits_only) == 13:
        return digits_only
    if "-" in raw_value and digits_only and len(digits_only) % 2 == 0:
        return digits_only

    return raw_value


def calculate_ean13_check_digit(base_value):
    digits = str(base_value or "").strip()
    if not digits.isdigit() or len(digits) != 12:
        return None

    odd_sum = sum(int(digit) for digit in digits[::2])
    even_sum = sum(int(digit) for digit in digits[1::2])
    total = odd_sum + (even_sum * 3)
    return str((10 - (total % 10)) % 10)


def append_ean13_check_digit(base_value):
    digits = str(base_value or "").strip()
    check_digit = calculate_ean13_check_digit(digits)
    if check_digit is None:
        return digits
    return f"{digits}{check_digit}"


def generate_code39_svg(barcode, compact=False):
    barcode = str(barcode or "").strip().upper()
    if not barcode:
        return None

    allowed_chars = set(CODE39_PATTERNS.keys()) - {"*"}
    if any(char not in allowed_chars for char in barcode):
        return None

    encoded = f"*{barcode}*"
    narrow_width = 1.42 if compact else 1.35
    wide_width = narrow_width * (2.15 if compact else 2.6)
    inter_char_gap = narrow_width
    quiet_zone = narrow_width * (2.4 if compact else 10)
    top_margin = 0.35 if compact else 6
    bar_height = 42 if compact else 46
    text_y = 42 if compact else 64

    total_width = quiet_zone * 2
    for char in encoded:
        total_width += sum(wide_width if unit == "w" else narrow_width for unit in CODE39_PATTERNS[char])
        total_width += inter_char_gap

    width = total_width
    height = 44 if compact else 72
    x_position = quiet_zone
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="{height}" viewBox="0 0 {width:.2f} {height}" role="img" aria-label="Code 39 barkod">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    for char in encoded:
        pattern = CODE39_PATTERNS[char]
        for index, unit in enumerate(pattern):
            element_width = wide_width if unit == "w" else narrow_width
            is_bar = index % 2 == 0
            if is_bar:
                lines.append(
                    f'<rect x="{x_position:.2f}" y="{top_margin}" width="{element_width:.2f}" height="{bar_height}" fill="#111111"/>'
                )
            x_position += element_width
        x_position += inter_char_gap

    lines.extend(
        [
            (
                f'<text x="{width / 2:.2f}" y="{text_y}" text-anchor="middle" '
                f'font-size="7.2" letter-spacing="0.6" font-family="Arial, sans-serif" fill="#111111">{barcode}</text>'
                if not compact else ""
            ),
            "</svg>",
        ]
    )
    return "".join(lines)


def get_code128_values(barcode):
    value = str(barcode or "").strip()
    if not value or any(ord(char) < 32 or ord(char) > 126 for char in value):
        return []

    # Unit labels follow 12 digits + a two-digit unit suffix. Set C keeps the
    # numeric base compact, then Set B preserves the literal -01/-02 suffix.
    if len(value) == 15 and value[:12].isdigit() and value[12] == "-" and value[13:].isdigit():
        values = [105] + [int(value[index:index + 2]) for index in range(0, 12, 2)] + [100]
        values.extend(ord(char) - 32 for char in value[12:])
    else:
        values = [104] + [ord(char) - 32 for char in value]

    checksum = values[0] + sum(code * index for index, code in enumerate(values[1:], start=1))
    return values + [checksum % 103, 106]


def generate_code128_svg(barcode, compact=False):
    values = get_code128_values(barcode)
    if not values:
        return None

    module_width = 1.0
    quiet_zone = 10 * module_width
    top_margin = 0.35 if compact else 6
    bar_height = 42 if compact else 46
    text_y = 42 if compact else 64
    barcode = str(barcode).strip()
    width = (quiet_zone * 2) + sum(sum(int(unit) for unit in CODE128_PATTERNS[code]) for code in values)
    x_position = quiet_zone
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="{44 if compact else 72}" viewBox="0 0 {width:.2f} {44 if compact else 72}" role="img" aria-label="Code 128 barkod">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    for code in values:
        for index, unit in enumerate(CODE128_PATTERNS[code]):
            element_width = int(unit) * module_width
            if index % 2 == 0:
                lines.append(
                    f'<rect x="{x_position:.2f}" y="{top_margin}" width="{element_width:.2f}" height="{bar_height}" fill="#111111"/>'
                )
            x_position += element_width

    if not compact:
        lines.append(
            f'<text x="{width / 2:.2f}" y="{text_y}" text-anchor="middle" font-size="7.2" letter-spacing="0.6" font-family="Arial, sans-serif" fill="#111111">{barcode}</text>'
        )
    lines.append("</svg>")
    return "".join(lines)


def generate_ean13_svg(barcode, compact=False):
    if not barcode:
        return None
    if not str(barcode).isdigit() or len(str(barcode)) != 13:
        return generate_code39_svg(barcode, compact=compact)

    barcode = str(barcode)
    first_digit = barcode[0]
    left_digits = barcode[1:7]
    right_digits = barcode[7:]
    parity = PARITY_PATTERNS[first_digit]

    bits = ["101"]
    for index, digit in enumerate(left_digits):
        bits.append(L_PATTERNS[digit] if parity[index] == "L" else G_PATTERNS[digit])
    bits.append("01010")
    for digit in right_digits:
        bits.append(R_PATTERNS[digit])
    bits.append("101")
    pattern = "".join(bits)

    width = 135 if compact else 188
    height = 48 if compact else 90
    bar_width = 1.38 if compact else 1.35
    left_margin = 2.0 if compact else 18
    top_margin = 0.35 if compact else 8
    main_bar_height = 41 if compact else 58
    guard_bar_height = 45 if compact else 66

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="EAN-13 barkod">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    for index, bit in enumerate(pattern):
        if bit != "1":
            continue
        is_guard = index < 3 or 45 <= index < 50 or index >= len(pattern) - 3
        bar_height = guard_bar_height if is_guard else main_bar_height
        x_position = left_margin + (index * bar_width)
        lines.append(
            f'<rect x="{x_position:.2f}" y="{top_margin}" width="{bar_width:.2f}" height="{bar_height}" fill="#1a1a1a"/>'
        )

    lines.extend(
        [
            (
                f'<text x="8" y="82" font-size="12" font-family="Arial, sans-serif" fill="#1a1a1a">{first_digit}</text>'
                if not compact else ""
            ),
            (
                f'<text x="{left_margin + 7:.2f}" y="82" font-size="12" letter-spacing="1.7" font-family="Arial, sans-serif" fill="#1a1a1a">{left_digits}</text>'
                if not compact else ""
            ),
            (
                f'<text x="{left_margin + 55:.2f}" y="82" font-size="12" letter-spacing="1.7" font-family="Arial, sans-serif" fill="#1a1a1a">{right_digits}</text>'
                if not compact else ""
            ),
            "</svg>",
        ]
    )
    return "".join(lines)
