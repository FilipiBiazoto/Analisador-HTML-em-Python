"""
Um renderizador simples de HTML para Tkinter.
Suporta: <p>, <br>, <b>/<strong>, <i>/<em>, <u>, <h1>-<h6>, <a href>, <ul>, <ol>, <li>, <img src>

Como usar: python tkinter_html_renderer.py
Cole o HTML à esquerda e clique em "Renderizar".

Dependências opcionais:
- Pillow (para carregar imagens): pip install pillow

Observação: este não é um navegador completo. É uma aproximação para mostrar conteúdo básico.
"""
from html.parser import HTMLParser
import tkinter as tk
from tkinter import ttk
from tkinter import font
import webbrowser
import io

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

class SimpleHTMLParser(HTMLParser):
    def __init__(self, text_widget):
        super().__init__()
        self.text = text_widget
        self.tag_stack = []
        self.list_stack = []
        self.href = None
        self.image_refs = []  

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("b", "strong"):
            self.tag_stack.append('bold')
        elif tag in ("i", "em"):
            self.tag_stack.append('italic')
        elif tag == 'u':
            self.tag_stack.append('underline')
        elif tag in ('h1','h2','h3','h4','h5','h6'):
            self.tag_stack.append(tag)
            self.text.insert(tk.END, '\n')
        elif tag == 'br':
            self.text.insert(tk.END, '\n')
        elif tag == 'p':
            self.text.insert(tk.END, '\n')
            self.tag_stack.append('p')
        elif tag == 'a':
            href = attrs.get('href')
            self.href = href
            self.tag_stack.append('link')
        elif tag == 'ul':
            self.list_stack.append(('ul', None))
        elif tag == 'ol':
            self.list_stack.append(('ol', 1))
        elif tag == 'li':
            if not self.list_stack:
                marker = '\u2022 '  
            else:
                lt, idx = self.list_stack[-1]
                if lt == 'ul':
                    marker = '  \u2022 '
                else:
                    marker = f'  {idx}. '
                    self.list_stack[-1] = (lt, idx+1)
            self.text.insert(tk.END, marker)
            self.tag_stack.append('li')
        elif tag == 'img':
            src = attrs.get('src')
            if src:
                self._insert_image(src)

    def handle_endtag(self, tag):
        if tag in ('b','strong','i','em','u','p','li'):
            style_map = {
                'b':'bold','strong':'bold','i':'italic','em':'italic','u':'underline','p':'p','li':'li'
            }
            style = style_map.get(tag)
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i] == style:
                    del self.tag_stack[i]
                    break
        elif tag in ('h1','h2','h3','h4','h5','h6'):
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i] == tag:
                    del self.tag_stack[i]
                    break
            self.text.insert(tk.END, '\n')
        elif tag == 'a':
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i] == 'link':
                    del self.tag_stack[i]
                    break
            self.href = None
        elif tag in ('ul','ol'):
            if self.list_stack:
                self.list_stack.pop()

    def handle_data(self, data):
        if not data:
            return
        start_index = self.text.index(tk.END)
        self.text.insert(tk.END, data)
        end_index = self.text.index(tk.END)

        for t in self.tag_stack:
            if t in ('h1','h2','h3','h4','h5','h6'):
                self.text.tag_add(t, start_index, end_index)
            elif t == 'p':
                pass
            elif t == 'bold':
                self.text.tag_add('bold', start_index, end_index)
            elif t == 'italic':
                self.text.tag_add('italic', start_index, end_index)
            elif t == 'underline':
                self.text.tag_add('underline', start_index, end_index)
            elif t == 'link' and self.href:
              
                tag_name = f'link_{start_index.replace(".","_")}'
                self.text.tag_add(tag_name, start_index, end_index)
                self.text.tag_bind(tag_name, '<Button-1>', lambda e, url=self.href: webbrowser.open(url))
                self.text.tag_config(tag_name, foreground='blue', underline=1)

    def _insert_image(self, src):
        try:
            if src.startswith('http://') or src.startswith('https://'):
               
                raise ValueError('Carregamento por URL não suportado neste demo. Use caminho local.')
            
            if PIL_AVAILABLE:
                img = Image.open(src)
               
                maxw, maxh = 400, 400
                w, h = img.size
                ratio = min(1, maxw/w, maxh/h)
                if ratio < 1:
                    img = img.resize((int(w*ratio), int(h*ratio)), Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(img)
            else:
               
                photo = tk.PhotoImage(file=src)
            self.image_refs.append(photo)
            self.text.image_create(tk.END, image=photo)
            self.text.insert(tk.END, '\n')
        except Exception as e:
            self.text.insert(tk.END, f'[Erro ao carregar imagem: {e}]\n')

class HTMLViewer(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=True)
        self._build_ui()

    def _build_ui(self):
        self.master.title('Renderizador HTML simples (Tkinter)')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=2)

        lbl = ttk.Label(left, text='HTML de entrada:')
        lbl.pack(anchor='nw', padx=6, pady=6)
        self.input_text = tk.Text(left, width=60, height=30)
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, padx=6, pady=(0,6))
        render_btn = ttk.Button(btn_frame, text='Renderizar', command=self.render_html)
        render_btn.pack(side=tk.LEFT)
        clear_btn = ttk.Button(btn_frame, text='Limpar saída', command=self.clear_output)
        clear_btn.pack(side=tk.LEFT, padx=6)

        lbl2 = ttk.Label(right, text='Visualização:')
        lbl2.pack(anchor='nw', padx=6, pady=6)

        self.output_text = tk.Text(right, wrap='word')
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))

        default_font = font.nametofont('TkDefaultFont')
        self.output_text.tag_config('bold', font=(default_font.actual('family'), default_font.actual('size'), 'bold'))
        self.output_text.tag_config('italic', font=(default_font.actual('family'), default_font.actual('size'), 'italic'))
        self.output_text.tag_config('underline', underline=1)

        base_family = default_font.actual('family')
        self.output_text.tag_config('h1', font=(base_family, 22, 'bold'))
        self.output_text.tag_config('h2', font=(base_family, 18, 'bold'))
        self.output_text.tag_config('h3', font=(base_family, 16, 'bold'))
        self.output_text.tag_config('h4', font=(base_family, 14, 'bold'))
        self.output_text.tag_config('h5', font=(base_family, 12, 'bold'))
        self.output_text.tag_config('h6', font=(base_family, 10, 'bold'))

    def clear_output(self):
        self.output_text.delete('1.0', tk.END)

    def render_html(self):
        html = self.input_text.get('1.0', tk.END)
        self.clear_output()
        parser = SimpleHTMLParser(self.output_text)
        parser.feed(html)
        parser.close()

def main():
    root = tk.Tk()
    root.geometry('1000x700')
    app = HTMLViewer(master=root)
    sample = '''<h1>Exemplo</h1>
<p>Este é um <b>texto em negrito</b>, <i>itálico</i> e um <a href="https://www.python.org">link para Python</a>.</p>
<p>Lista:</p>
<ul><li>Item 1</li><li>Item 2</li></ul>
<p>Imagem local (se existir):</p>
<img src="example.png">
'''
    app.input_text.insert('1.0', sample)
    root.mainloop()

if __name__ == '__main__':
    main()