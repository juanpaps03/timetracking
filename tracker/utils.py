def column_letter(idx):
    if idx < 26:
        return chr(ord('A')+idx)
    elif idx < 52:
        return 'A%s' % column_letter(idx-26)


def column_number(letter):
    if len(letter) == 1:
        return ord(letter) - ord('A')
    else:
        return 26 + column_number(letter[1:])
