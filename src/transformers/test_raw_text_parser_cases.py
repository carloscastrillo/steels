from parse_request_from_raw_text import parse_request_from_raw_text


TEST_CASES = [
    {
        "name": "etiquetado limpio",
        "text": """
Cliente: HIJOS DE ANGEL BALLESTER S.L.
Referencia: PRUEBA 007
Producto: CRC
Calidad: DC01 AM O
Espesor: 0,8
Ancho: 1250
CW min: 15000
CW max: 20000
Toneladas: 95
Fecha: 2026-04-18
Notas: caso limpio
""".strip(),
    },
    {
        "name": "texto comercial breve",
        "text": "Hijos de Angel Ballester necesita 80 tn de CRC DC01 AM O en 0,8 x 1250, coil entre 15 y 20 tn, fecha 2026-04-17, ref PRUEBA 008.",
    },
    {
        "name": "texto corto con slash y fecha española",
        "text": "Pedido para HIJOS DE ANGEL BALLESTER S.L. 90 tn CRC DC01 AM O 0,8x1250 cw 15-20 fecha 17/04/2026 ref P009",
    },
    {
        "name": "texto sucio con menos etiquetas",
        "text": "Ballester / CRC / DC01 AM O / 70 tn / 0,8 x 1250 / coil 15 y 20 / urgente / ref P010",
    },
    {
        "name": "texto con orden distinto",
        "text": "Ref P011. Para el 2026-04-19, 110 toneladas de CRC DC01 AM O 0,8x1250 para HIJOS DE ANGEL BALLESTER S.L., cw entre 15000 y 20000.",
    },
]


def main():
    for idx, case in enumerate(TEST_CASES, start=1):
        print("=" * 120)
        print(f"CASO {idx}: {case['name']}")
        print("-" * 120)
        print(case["text"])
        print("\nPARSEADO")
        print("-" * 120)

        parsed = parse_request_from_raw_text(case["text"])
        for key, value in parsed.items():
            print(f"{key}: {value}")
        print()


if __name__ == "__main__":
    main()