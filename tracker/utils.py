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



def traducir_mes(num):
    if num == 1:
        return 'ENERO'
    else:
        if num == 2:
            return 'FEBRERO'
        else:
            if num == 3:
                return 'MARZO'
            else:
                if num == 4:
                    return 'ABRIL'
                else:
                    if num == 5:
                        return 'MAYO'
                    else:
                        if num == 6:
                            return 'JUNIO'
                        else:
                            if num == 7:
                                return 'JULIO'
                            else:
                                if num == 8:
                                    return 'AGOSTO'
                                else:
                                    if num == 9:
                                        return 'SEPTIEMBRE'
                                    else:
                                        if num == 10:
                                            return 'OCTUBRE'
                                        else:
                                            if num == 11:
                                                return 'NOVIEMBRE'
                                            else:
                                                if num == 12:
                                                    return 'DICIEMBRE'

