"""
Um Mini Navegador Web Simples (Baseado em Tkinter)

Funcionalidades Adicionadas:
1. Barra de Endereços (URL) para carregar páginas web reais (usando 'requests').
2. Botão 'Ir' para iniciar o carregamento da URL.
3. Tratamento de erros de rede (ex: 404, falha de conexão).
4. Melhoria na interface para se assemelhar a um navegador.
5. Suporte a imagens de URLs (requer Pillow).
6. Remoção da área de entrada HTML, focando na navegação.

Dependências:
- requests: pip install requests
- Pillow (opcional, para imagens): pip install pillow
"""
from html.parser import HTMLParser
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font
import webbrowser
import requests
import io

# Tenta importar Pillow para suporte a imagens
try:
    from PIL import Image, ImageTk
    # Definir um filtro de redimensionamento de alta qualidade
    Image.ANTIALIAS = Image.Resampling.LANCZOS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
except Exception:
    PIL_AVAILABLE = False

class SimpleHTMLParser(HTMLParser):
    """
    Analisador HTML que renderiza o conteúdo em um widget tk.Text.
    """
    def __init__(self, text_widget, base_url=""):
        super().__init__()
        self.text = text_widget
        self.tag_stack = []
        self.list_stack = []
        self.href = None
        self.image_refs = []
        self.base_url = base_url # URL base para resolver caminhos relativos
        self.color_tag_map = {} # Mapeamento de cor (hex) para nome de tag seguro

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        
        # Estilos de texto
        if tag in ("b", "strong"):
            self.tag_stack.append('bold')
        elif tag in ("i", "em"):
            self.tag_stack.append('italic')
        elif tag == 'u':
            self.tag_stack.append('underline')
        elif tag == 'font':
            color = attrs.get('color')
            if color:
                self.tag_stack.append(f'color_{color}')
        
        # Cabeçalhos e parágrafos
        elif tag in ('h1','h2','h3','h4','h5','h6'):
            self.tag_stack.append(tag)
            self.text.insert(tk.END, '\n')
        elif tag == 'br':
            self.text.insert(tk.END, '\n')
        elif tag == 'p':
            self.text.insert(tk.END, '\n')
            self.tag_stack.append('p')
        
        # Links
        elif tag == 'a':
            href = attrs.get('href')
            if href:
                # Tenta resolver URL relativa
                if not href.startswith(('http://', 'https://', 'file://')):
                    import urllib.parse
                    href = urllib.parse.urljoin(self.base_url, href)
                self.href = href
                self.tag_stack.append('link')
        
        # Listas
        elif tag == 'ul':
            self.text.insert(tk.END, '\n')
            self.list_stack.append(('ul', None))
        elif tag == 'ol':
            self.text.insert(tk.END, '\n')
            self.list_stack.append(('ol', 1))
        elif tag == 'li':
            # Determinar o nível de indentação
            indent_level = len(self.list_stack)
            indent = '    ' * (indent_level - 1) # 4 espaços por nível de indentação

            # Inserir quebra de linha e indentação antes do item de lista
            if self.text.index(tk.END) != '1.0' and self.text.get(f'{self.text.index(tk.END)} -1c') != '\n':
                self.text.insert(tk.END, '\n')
            
            self.text.insert(tk.END, indent)

            # Determinar o marcador
            if not self.list_stack:
                marker = '\u2022 '  # Fallback
            else:
                lt, idx = self.list_stack[-1]
                if lt == 'ul':
                    marker = '\u2022 '
                else:
                    marker = f'{idx}. '
                    self.list_stack[-1] = (lt, idx+1)
            
            self.text.insert(tk.END, marker)
            self.tag_stack.append('li')
        
        # Imagens
        elif tag == 'img':
            src = attrs.get('src')
            if src:
                # Tenta resolver URL relativa
                if not src.startswith(('http://', 'https://', 'file://')):
                    import urllib.parse
                    src = urllib.parse.urljoin(self.base_url, src)
                self._insert_image(src)

    def handle_endtag(self, tag):
        # Lógica de remoção de tags da pilha (simplificada)
        style_map = {
            'b':'bold','strong':'bold','i':'italic','em':'italic','u':'underline','p':'p','li':'li',
            'h1':'h1','h2':'h2','h3':'h3','h4':'h4','h5':'h5','h6':'h6'
        }
        style = style_map.get(tag)
        if style:
            if style in self.tag_stack:
                self.tag_stack.remove(style)
            if tag.startswith('h'):
                self.text.insert(tk.END, '\n')
        elif tag == 'a':
            if 'link' in self.tag_stack:
                self.tag_stack.remove('link')
            self.href = None
        elif tag in ('ul','ol'):
            if self.list_stack:
                self.list_stack.pop()
            self.text.insert(tk.END, '\n')
        elif tag == 'font':
            # Remove a tag de cor correspondente da pilha
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i].startswith('color_'):
                    del self.tag_stack[i]
                    break

    def handle_data(self, data):
        if not data:
            return

        # Normalizar múltiplos espaços em branco para um único espaço
        normalized_data = ' '.join(data.split())
        if not normalized_data:
            return

        # Lógica para evitar espaços duplicados
        if self.text.index(tk.END) != '1.0':
            last_char = self.text.get(f'{self.text.index(tk.END)} -1c')
            if last_char not in ('\n', ' ') and data.startswith(' '):
                normalized_data = ' ' + normalized_data
            elif last_char == ' ' and data.startswith(' '):
                normalized_data = normalized_data.lstrip()
        
        start_index = self.text.index(tk.END)
        self.text.insert(tk.END, normalized_data)
        end_index = self.text.index(tk.END)

        for t in self.tag_stack:
            if t in ('h1','h2','h3','h4','h5','h6'):
                self.text.tag_add(t, start_index, end_index)
            elif t == 'bold':
                self.text.tag_add('bold', start_index, end_index)
            elif t == 'italic':
                self.text.tag_add('italic', start_index, end_index)
            elif t == 'underline':
                self.text.tag_add('underline', start_index, end_index)
            elif t.startswith('color_'):
                color_hex = t.split('_')[1]
                
                # 1. Obter o nome da tag segura
                if color_hex not in self.color_tag_map:
                    # Cria um nome de tag seguro (ex: 'color_tag_1')
                    tag_name = f'color_tag_{len(self.color_tag_map) + 1}'
                    self.color_tag_map[color_hex] = tag_name
                    
                    # 2. Configurar a tag com a cor real
                    self.text.tag_config(tag_name, foreground=color_hex)
                
                # 3. Aplicar a tag ao texto
                safe_tag_name = self.color_tag_map[color_hex]
                self.text.tag_add(safe_tag_name, start_index, end_index)
            elif t == 'link' and self.href:
                tag_name = f'link_{start_index.replace(".","_")}'
                self.text.tag_add(tag_name, start_index, end_index)
                
                def open_link(event, url=self.href):
                    webbrowser.open(url)
                
                self.text.tag_bind(tag_name, '<Button-1>', open_link)
                self.text.tag_config(tag_name, foreground='#0078D7', underline=1)

    def _insert_image(self, src):
        if not PIL_AVAILABLE:
            self.text.insert(tk.END, f'[Imagem: {src} - Pillow não instalado]\n')
            return

        try:
            img_data = None
            if src.startswith(('http://', 'https://')):
                # Carregar imagem de URL
                response = requests.get(src, stream=True, timeout=5)
                response.raise_for_status()
                img_data = response.content
                img = Image.open(io.BytesIO(img_data))
            else:
                # Carregar imagem local
                img = Image.open(src)
            
            # Redimensionamento
            maxw, maxh = 400, 400
            w, h = img.size
            ratio = min(1, maxw/w, maxh/h)
            if ratio < 1:
                img = img.resize((int(w*ratio), int(h*ratio)), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            
            self.image_refs.append(photo)
            self.text.image_create(tk.END, image=photo)
            self.text.insert(tk.END, '\n')
        except requests.exceptions.RequestException as e:
            self.text.insert(tk.END, f'[Erro de Rede ao carregar imagem: {e}]\n')
        except Exception as e:
            self.text.insert(tk.END, f'[Erro ao carregar imagem: {e}]\n')

class MiniBrowser(tk.Frame):
    """
    Interface principal do Mini Navegador.
    """
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=True)
        self.current_url = ""
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        style = ttk.Style()
        available_themes = style.theme_names()
        
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')
        
        self.text_bg = '#FFFFFF'
        self.text_fg = '#333333'
        self.font_family = 'Segoe UI' if 'Segoe UI' in font.families() else 'Helvetica'
        self.font_size = 11
        
        style.configure('TButton', font=(self.font_family, self.font_size, 'bold'), padding=6)
        style.map('TButton', background=[('active', '#E1E1E1')])
        style.configure('TLabel', font=(self.font_family, self.font_size, 'bold'), foreground='#333333')
        style.configure('TEntry', font=(self.font_family, self.font_size), padding=5)

    def _build_ui(self):
        self.master.title('Mini Navegador Web (Tkinter)')
        self.master.geometry('800x600')
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 1. Barra de Endereços (URL Bar)
        url_frame = ttk.Frame(self, padding="10 10 10 5")
        url_frame.grid(row=0, column=0, sticky='ew')
        url_frame.columnconfigure(1, weight=1)

        lbl = ttk.Label(url_frame, text='URL:', style='TLabel')
        lbl.grid(row=0, column=0, sticky='w', padx=(0, 5))
        
        self.url_entry = ttk.Entry(url_frame, style='TEntry')
        self.url_entry.grid(row=0, column=1, sticky='ew')
        self.url_entry.insert(0, "https://www.w3schools.com/w3css/tryw3css_templates_gourmet_catering.htm") # URL de exemplo
        self.url_entry.bind('<Return>', lambda event: self.load_url()) # Carregar ao pressionar Enter
        
        go_btn = ttk.Button(url_frame, text='Ir', command=self.load_url, style='TButton')
        go_btn.grid(row=0, column=2, sticky='e', padx=(5, 0))
        
        local_html_btn = ttk.Button(url_frame, text='HTML Local', command=self.show_local_html_input, style='TButton')
        local_html_btn.grid(row=0, column=3, sticky='e', padx=(5, 0))

        # 2. Área de Visualização (Output)
        output_frame = ttk.Frame(self, padding="10 5 10 10")
        output_frame.grid(row=1, column=0, sticky='nsew')
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        output_scroll = ttk.Scrollbar(output_frame)
        output_scroll.grid(row=0, column=1, sticky='ns')
        
        self.output_text = tk.Text(output_frame, 
                                   wrap='word', 
                                   font=(self.font_family, self.font_size), 
                                   bg=self.text_bg, 
                                   fg=self.text_fg, 
                                   yscrollcommand=output_scroll.set,
                                   relief=tk.FLAT,
                                   padx=10, pady=10,
                                   state=tk.DISABLED) # Desabilitar edição
        self.output_text.grid(row=0, column=0, sticky='nsew')
        output_scroll.config(command=self.output_text.yview)
        
        # Configuração das Tags de Estilo
        self._configure_tags()

    def show_local_html_input(self):
        """Abre uma nova janela para injetar HTML localmente."""
        
        # Cria a nova janela
        top = tk.Toplevel(self.master)
        top.title("Injetar HTML Local")
        top.geometry("600x400")
        top.columnconfigure(0, weight=1)
        top.rowconfigure(1, weight=1)

        # Rótulo
        lbl = ttk.Label(top, text='Cole o HTML abaixo:', style='TLabel')
        lbl.grid(row=0, column=0, sticky='nw', padx=10, pady=5)

        # Área de entrada de texto com scrollbar
        input_frame = ttk.Frame(top)
        input_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=5)
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)
        
        input_scroll = ttk.Scrollbar(input_frame)
        input_scroll.grid(row=0, column=1, sticky='ns')
        
        input_text = tk.Text(input_frame, 
                             wrap='word', 
                             font=(self.font_family, self.font_size), 
                             bg=self.text_bg, 
                             fg=self.text_fg, 
                             yscrollcommand=input_scroll.set,
                             relief=tk.FLAT,
                             padx=5, pady=5)
        input_text.grid(row=0, column=0, sticky='nsew')
        input_scroll.config(command=input_text.yview)
        
        # Botão Renderizar
        def render_local():
            html_content = input_text.get('1.0', tk.END)
            self.render_html(html_content, base_url="") # base_url vazia para HTML local
            top.destroy() # Fecha a janela de entrada após renderizar

        render_btn = ttk.Button(top, text='Renderizar', command=render_local, style='TButton')
        render_btn.grid(row=2, column=0, sticky='e', padx=10, pady=10)

        # Exemplo de HTML para facilitar o teste
        sample = '''<h1>Exemplo de Renderização HTML</h1>
<p>Este é um <b>texto em negrito</b>, <i>itálico</i> e <u>sublinhado</u>.
<br>Aqui está uma quebra de linha.</p>
<h2>Lista de Tecnologias</h2>
<p>Lista não ordenada:</p>
<ul>
    <li>Item 1: Python</li>
    <br>
    <li>Item 2: Tkinter</li>
    <br>
    <li>Item 3: <a href="https://www.python.org">Link para Python</a></li>
</ul>
<p>Lista ordenada:</p>
<ol>
    <li>Primeiro passo</li>
    <br>
    <li>Segundo passo</li>
    <br>
    <li>Terceiro passo</li>
</ol>
<h3>Imagem Local</h3>
<p>Imagem local (se existir):</p>
<br><br>
<img src="foto.png">'''
        input_text.insert('1.0', sample)

    def _configure_tags(self):
        # Estilos básicos
        self.output_text.tag_config('bold', font=(self.font_family, self.font_size, 'bold'))
        self.output_text.tag_config('italic', font=(self.font_family, self.font_size, 'italic'))
        self.output_text.tag_config('underline', underline=1)

        # Estilos de cabeçalho
        base_family = self.font_family
        self.output_text.tag_config('h1', font=(base_family, 24, 'bold'), spacing3=10)
        self.output_text.tag_config('h2', font=(base_family, 18, 'bold'), spacing3=8)
        self.output_text.tag_config('h3', font=(base_family, 14, 'bold'), spacing3=6)
        self.output_text.tag_config('h4', font=(base_family, 12, 'bold'), spacing3=4)
        self.output_text.tag_config('h5', font=(base_family, 11, 'bold'), spacing3=2)
        self.output_text.tag_config('h6', font=(base_family, 10, 'bold'), spacing3=2)
        
        # Estilo para parágrafo
        self.output_text.tag_config('p', spacing3=5)
        
        # Configuração de tags de cor (para a tag <font>)
        # Como não sabemos as cores exatas que o usuário usará, 
        # vamos configurar as tags de cor no momento da renderização (handle_data)
        # e não aqui, mas a lógica de handle_data foi simplificada para usar o nome da cor como tag.

    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        # Limpar referências de imagem
        parser = getattr(self, 'last_parser', None)
        if parser:
            parser.image_refs = []
        self.output_text.config(state=tk.DISABLED)

    def load_url(self):
        url = self.url_entry.get()
        if not url:
            return

        # Adicionar http:// se não houver protocolo
        if not url.startswith(('http://', 'https://', 'file://')):
            url = 'http://' + url
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)

        self.clear_output()
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"Carregando: {url}...\n\n")
        self.output_text.config(state=tk.DISABLED)
        self.update_idletasks() # Força a atualização da interface

        try:
            # Faz a requisição HTTP
            response = requests.get(url, timeout=10)
            response.raise_for_status() # Levanta exceção para códigos de status ruins (4xx ou 5xx)
            
            html_content = response.text
            self.current_url = url
            
            self.render_html(html_content, url)

        except requests.exceptions.Timeout:
            self.show_error("Erro de Tempo Limite", f"A requisição para {url} excedeu o tempo limite.")
        except requests.exceptions.ConnectionError:
            self.show_error("Erro de Conexão", f"Não foi possível conectar a {url}. Verifique a URL ou sua conexão.")
        except requests.exceptions.HTTPError as e:
            self.show_error("Erro HTTP", f"Erro ao carregar {url}: {e}")
        except Exception as e:
            self.show_error("Erro Desconhecido", f"Ocorreu um erro inesperado: {e}")

    def render_html(self, html_content, base_url):
        self.clear_output()
        self.output_text.config(state=tk.NORMAL)
        
        # Cria e armazena o parser para manter as referências de imagem
        parser = SimpleHTMLParser(self.output_text, base_url=base_url)
        self.last_parser = parser
        
        try:
            parser.feed(html_content)
        except Exception as e:
            self.output_text.insert(tk.END, f"\n[Erro durante a análise do HTML: {e}]")
        finally:
            parser.close()
            self.output_text.config(state=tk.DISABLED)
            self.output_text.yview_moveto(0) # Rola para o topo

    def show_error(self, title, message):
        self.clear_output()
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"--- {title} ---\n\n{message}\n")
        self.output_text.config(state=tk.DISABLED)
        messagebox.showerror(title, message)

def main():
    # Instalar requests se não estiver presente (para garantir que o código funcione)
    try:
        import requests
    except ImportError:
        print("O módulo 'requests' não está instalado. Instalando...")
        import subprocess
        try:
            subprocess.check_call(['pip3', 'install', 'requests'])
            import requests # Tenta importar novamente
        except Exception as e:
            print(f"Falha ao instalar 'requests': {e}")
            print("O navegador não poderá carregar URLs externas.")
            
    # Instalar Pillow se não estiver presente (para suporte a imagens)
    if not PIL_AVAILABLE:
        print("O módulo 'Pillow' não está instalado. Instalando...")
        import subprocess
        try:
            subprocess.check_call(['pip3', 'install', 'Pillow'])
            # Não é necessário reimportar aqui, o código principal usará a variável PIL_AVAILABLE
        except Exception as e:
            print(f"Falha ao instalar 'Pillow': {e}")
            print("O navegador não terá suporte completo a imagens.")

    root = tk.Tk()
    root.option_add('*tearOff', tk.FALSE)
    app = MiniBrowser(master=root)
    root.mainloop()

if __name__ == '__main__':
    main()