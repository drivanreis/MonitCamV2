"""
Seletor de Área da Tela - MonitCamV2
Permite selecionar uma área da tela clicando e arrastando.
Retorna as coordenadas no formato x,y,w,h para stdout.
"""

import tkinter as tk
from PIL import ImageGrab
import sys


class ScreenSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.3)
        self.root.configure(bg='grey')
        self.root.config(cursor='crosshair')
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg='grey')
        self.canvas.pack(fill='both', expand=True)
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.selection = None
        
        # Binds de mouse
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        
        # ESC para cancelar
        self.root.bind('<Escape>', lambda e: self.cancel())
        
        # Adiciona texto de instrução
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.canvas.create_text(
            screen_width // 2, 
            50, 
            text='Clique e arraste para selecionar a área (ESC para cancelar)',
            font=('Arial', 16, 'bold'),
            fill='white'
        )
    
    def on_mouse_down(self, event):
        """Inicia a seleção"""
        self.start_x = event.x
        self.start_y = event.y
        
        # Remove retângulo anterior se existir
        if self.rect:
            self.canvas.delete(self.rect)
        
        # Cria novo retângulo
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=3
        )
    
    def on_mouse_drag(self, event):
        """Atualiza o retângulo durante o arrasto"""
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)
    
    def on_mouse_up(self, event):
        """Finaliza a seleção"""
        if not self.start_x or not self.start_y:
            return
        
        end_x = event.x
        end_y = event.y
        
        # Calcula coordenadas normalizadas (garante que x1 < x2 e y1 < y2)
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        # Calcula largura e altura
        w = x2 - x1
        h = y2 - y1
        
        # Valida área mínima (10x10 pixels)
        if w < 10 or h < 10:
            self.cancel()
            return
        
        # Salva seleção
        self.selection = (int(x1), int(y1), int(w), int(h))
        self.root.quit()
    
    def cancel(self):
        """Cancela a seleção"""
        self.selection = None
        self.root.quit()
    
    def run(self):
        """Executa o seletor e retorna as coordenadas"""
        self.root.mainloop()
        self.root.destroy()
        return self.selection


def main():
    """Função principal"""
    try:
        selector = ScreenSelector()
        selection = selector.run()
        
        if selection:
            # Imprime as coordenadas no formato x,y,w,h
            print(f"{selection[0]},{selection[1]},{selection[2]},{selection[3]}")
            sys.exit(0)
        else:
            # Seleção cancelada
            sys.exit(1)
    except Exception as e:
        print(f"ERRO: {str(e)}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
