def column_letter(idx):
    column_name = ""
    while idx > 0:
        idx, remainder = divmod(idx - 1, 26)
        column_name = chr(65 + remainder) + column_name
    return column_name


def column_number(letter):
    if len(letter) == 1:
        return ord(letter) - ord('A')
    else:
        return 26 + column_number(letter[1:])

