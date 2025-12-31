"""
Ponto de entrada principal da aplicação MonitCam.
Inicia o servidor Flask e abre o navegador.
"""

import sys


def main():
    """
    Função principal que inicia o servidor Flask.
    """
    print("=" * 60)
    print("MonitCam - Sistema de Monitoramento por Captura de Tela")
    print("=" * 60)
    print("\nIniciando servidor...")
    print("Interface: http://127.0.0.1:5000")
    print("\nPressione Ctrl+C para encerrar.")
    print("=" * 60)
    
    try:
        from server import run_server
        run_server()
    except ImportError as e:
        print(f"\nERRO: {e}")
        print("Execute: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nEncerrando aplicação...")
        sys.exit(0)
    except Exception as e:
        print(f"\nERRO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
