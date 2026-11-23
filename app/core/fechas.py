""" calculo de la fecha de vencimiento de la membresia """

import calendar 
from datetime import date 



def calcular_vencimiento(fecha_inicio: date, meses: int)  -> date:

    """ Si ese día no existe en el mes de destino, usa el último día del mes:
    - 31/01 + 1 mes  -> 28/02 (o 29/02 en año bisiesto)
    - 31/03 + 1 mes  -> 30/04
    - 15/01 + 1 mes  -> 15/02
    - 30/11 + 3 meses -> 28/02 del año siguiente"""


    if meses <1:
        raise ValueError("El numero debe de ser de al menos 1 mes")

    total = fecha_inicio.month - 1 + meses 
    anio = fecha_inicio.year + total // 12 
    mes = total % 12 + 1 
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    dia = min(fecha_inicio.day, ultimo_dia)
    return date(anio, mes, dia)
