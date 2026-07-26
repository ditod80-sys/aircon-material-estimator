import ezdxf


def read_dwg(file_path):
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()

        print("=" * 50)
        print(f"파일 : {file_path}")
        print("=" * 50)

        print("\n[레이어 목록]")
        for layer in doc.layers:
            print(f"- {layer.dxf.name}")

        print("\n[도면 객체 개수]")
        print(len(msp))

        print("\n[TEXT / MTEXT]")
        for entity in msp:
            if entity.dxftype() in ("TEXT", "MTEXT"):
                try:
                    print(entity.plain_text())
                except Exception:
                    print(entity.dxf.text)

    except Exception as e:
        print("오류 :", e)