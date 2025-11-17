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
from html.parser import HTMLParser  # — Importa a classe base para análise de HTML simples
import tkinter as tk  # — Importa tkinter com o alias 'tk' para UI
from tkinter import ttk, messagebox  # — Importa widgets temáticos (ttk) e messagebox para diálogos
from tkinter import font  # — Importa utilitários de fonte do tkinter
import webbrowser  # — Permite abrir links no navegador do sistema
import requests  # — Biblioteca para fazer requisições HTTP
import io  # — Utilitário para trabalhar com buffers em memória (usado ao ler imagens remotas)

# Tenta importar Pillow para suporte a imagens
try:
    from PIL import Image, ImageTk  # — Importa Image para abrir/redimensionar e ImageTk para integrar com Tk
    # Definir um filtro de redimensionamento de alta qualidade
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # — Ajusta alias para usar LANCZOS (alta qualidade)
    PIL_AVAILABLE = True  # — Marca que Pillow está disponível
except ImportError:
    PIL_AVAILABLE = False  # — Pillow não está instalado
except Exception:
    PIL_AVAILABLE = False  # — Qualquer outro erro também resulta em Pillow indisponível

class SimpleHTMLParser(HTMLParser):
    """
    Analisador HTML que renderiza o conteúdo em um widget tk.Text.
    """
    def __init__(self, text_widget, base_url=""):
        super().__init__()
        self.text = text_widget  # — Text widget onde o conteúdo será inserido
        self.tag_stack = []  # — Pilha de tags para aplicar estilos abertos
        self.list_stack = []  # — Pilha para controle de listas (ul/ol)
        self.href = None  # — URL atualmente em contexto de <a>
        self.image_refs = []  # — Referências a imagens para evitar GC
        self.base_url = base_url  # — URL base para resolver caminhos relativos

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)  # — Converte atributos em dicionário para acesso fácil
        
        # Estilos de texto
        if tag in ("b", "strong"):
            self.tag_stack.append('bold')  # — Marca negrito
        elif tag in ("i", "em"):
            self.tag_stack.append('italic')  # — Marca itálico
        elif tag == 'u':
            self.tag_stack.append('underline')  # — Marca sublinhado
        
        # Cabeçalhos e parágrafos
        elif tag in ('h1','h2','h3','h4','h5','h6'):
            self.tag_stack.append(tag)  # — Marca qual header está aberto
            self.text.insert(tk.END, '\n')  # — Quebra de linha antes do cabeçalho
        elif tag == 'br':
            self.text.insert(tk.END, '\n')  # — Linha de quebra
        elif tag == 'p':
            self.text.insert(tk.END, '\n')  # — Quebra antes do parágrafo
            self.tag_stack.append('p')  # — Marca parágrafo (pode ser usado para espaçamento)
        
        # Links
        elif tag == 'a':
            href = attrs.get('href')  # — Obtém o atributo href, se existir
            if href:
                # Tenta resolver URL relativa
                if not href.startswith(('http://', 'https://', 'file://')):
                    import urllib.parse
                    href = urllib.parse.urljoin(self.base_url, href)  # — Resolve URL relativa com base_url
                self.href = href  # — Armazena href atual
                self.tag_stack.append('link')  # — Marca que estamos dentro de um link
        
        # Listas
        elif tag == 'ul':
            self.text.insert(tk.END, '\n')  # — Linha em branco antes da lista não ordenada
            self.list_stack.append(('ul', None))  # — Empilha tipo 'ul'
        elif tag == 'ol':
            self.text.insert(tk.END, '\n')  # — Linha em branco antes da lista ordenada
            self.list_stack.append(('ol', 1))  # — Empilha tipo 'ol' com índice inicial 1
        elif tag == 'li':
            # — Insere quebra de linha antes do item se não estivermos no início
            if self.text.index(tk.END) != '1.0' and self.text.get(f'{self.text.index(tk.END)} -1c') != '\n':
                self.text.insert(tk.END, '\n')
                
            if not self.list_stack:
                marker = '\u2022 '  # — Bullet padrão se lista não estiver conhecida
            else:
                lt, idx = self.list_stack[-1]
                if lt == 'ul':
                    marker = '  \u2022 '  # — Bullet para <ul>
                else:
                    marker = f'  {idx}. '  # — Número para <ol>
                    self.list_stack[-1] = (lt, idx+1)  # — Incrementa índice da lista ordenada
            self.text.insert(tk.END, marker)  # — Insere o marcador no Text
            self.tag_stack.append('li')  # — Marca que estamos dentro de um <li>
        
        # Imagens
        elif tag == 'img':
            src = attrs.get('src')  # — Obtém atributo src da imagem
            if src:
                # Tenta resolver URL relativa
                if not src.startswith(('http://', 'https://', 'file://')):
                    import urllib.parse
                    src = urllib.parse.urljoin(self.base_url, src)  # — Resolve src relativo
                self._insert_image(src)  # — Tenta inserir a imagem no Text

    def handle_endtag(self, tag):
        # Lógica de remoção de tags da pilha (simplificada)
        style_map = {
            'b':'bold','strong':'bold','i':'italic','em':'italic','u':'underline','p':'p','li':'li',
            'h1':'h1','h2':'h2','h3':'h3','h4':'h4','h5':'h5','h6':'h6'
        }
        style = style_map.get(tag)  # — Mapeia tag HTML para chave usada na pilha
        if style:
            if style in self.tag_stack:
                self.tag_stack.remove(style)  # — Remove a entrada correspondente da pilha
            if tag.startswith('h'):
                self.text.insert(tk.END, '\n')  # — Adiciona quebra após cabeçalho
        elif tag == 'a':
            if 'link' in self.tag_stack:
                self.tag_stack.remove('link')  # — Sai do contexto de link
            self.href = None  # — Limpa href armazenado
        elif tag in ('ul','ol'):
            if self.list_stack:
                self.list_stack.pop()  # — Remove a lista atual da pilha
            self.text.insert(tk.END, '\n')  # — Linha em branco após a lista

    def handle_data(self, data):
        if not data:
            return  # — Ignora strings vazias ou None

        # Normalizar múltiplos espaços em branco para um único espaço
        normalized_data = ' '.join(data.split())  # — Colapsa espaços repetidos
        if not normalized_data:
            return  # — Nada útil após normalização

        # Lógica para evitar espaços duplicados
        if self.text.index(tk.END) != '1.0':
            last_char = self.text.get(f'{self.text.index(tk.END)} -1c')  # — Último caractere atual no Text
            if last_char not in ('\n', ' ') and data.startswith(' '):
                normalized_data = ' ' + normalized_data  # — Preserva espaço inicial se necessário
            elif last_char == ' ' and data.startswith(' '):
                normalized_data = normalized_data.lstrip()  # — Remove espaço duplicado
        
        start_index = self.text.index(tk.END)  # — Marca índice inicial antes de inserir
        self.text.insert(tk.END, normalized_data)  # — Insere texto processado
        end_index = self.text.index(tk.END)  # — Índice após inserção

        for t in self.tag_stack:
            if t in ('h1','h2','h3','h4','h5','h6'):
                self.text.tag_add(t, start_index, end_index)  # — Aplica estilo de cabeçalho ao intervalo
            elif t == 'bold':
                self.text.tag_add('bold', start_index, end_index)  # — Aplica negrito
            elif t == 'italic':
                self.text.tag_add('italic', start_index, end_index)  # — Aplica itálico
            elif t == 'underline':
                self.text.tag_add('underline', start_index, end_index)  # — Aplica sublinhado
            elif t == 'link' and self.href:
                tag_name = f'link_{start_index.replace(".","_")}'  # — Gera nome único para a tag do link
                self.text.tag_add(tag_name, start_index, end_index)  # — Adiciona tag ao intervalo
                
                def open_link(event, url=self.href):
                    webbrowser.open(url)  # — Abre o link no navegador padrão
                
                self.text.tag_bind(tag_name, '<Button-1>', open_link)  # — Vincula clique à abertura do link
                self.text.tag_config(tag_name, foreground='#0078D7', underline=1)  # — Estilo visual do link

    def _insert_image(self, src):
        if not PIL_AVAILABLE:
            # — Se Pillow não está instalado, informa no texto que a imagem não pôde ser exibida
            self.text.insert(tk.END, f'[Imagem: {src} - Pillow não instalado]\n')
            return

        try:
            img_data = None
            if src.startswith(('http://', 'https://')):
                # Carregar imagem de URL
                response = requests.get(src, stream=True, timeout=5)  # — Baixa imagem com timeout
                response.raise_for_status()  # — Lança caso status HTTP seja erro
                img_data = response.content  # — Conteúdo binário da imagem
                img = Image.open(io.BytesIO(img_data))  # — Abre imagem a partir do buffer em memória
            else:
                # Carregar imagem local
                img = Image.open(src)  # — Abre imagem localmente
            
            # Redimensionamento
            maxw, maxh = 400, 400  # — Tamanho máximo para exibição da imagem
            w, h = img.size
            ratio = min(1, maxw/w, maxh/h)  # — Calcula fator de escala para caber no box
            if ratio < 1:
                img = img.resize((int(w*ratio), int(h*ratio)), Image.Resampling.LANCZOS)  # — Redimensiona com LANCZOS
            
            photo = ImageTk.PhotoImage(img)  # — Converte para objeto compatível com Tk
            
            self.image_refs.append(photo)  # — Armazena referência para evitar garbage collection
            self.text.image_create(tk.END, image=photo)  # — Insere imagem no Text
            self.text.insert(tk.END, '\n')  # — Quebra de linha após a imagem
        except requests.exceptions.RequestException as e:
            # — Erro específico de rede ao baixar a imagem
            self.text.insert(tk.END, f'[Erro de Rede ao carregar imagem: {e}]\n')
        except Exception as e:
            # — Qualquer outro erro ao carregar/processar a imagem
            self.text.insert(tk.END, f'[Erro ao carregar imagem: {e}]\n')

class MiniBrowser(tk.Frame):
    """
    Interface principal do Mini Navegador.
    """
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master  # — Janela pai (root)
        self.pack(fill=tk.BOTH, expand=True)  # — Preenche todo o espaço disponível
        self.current_url = ""  # — Armazena a URL atualmente carregada
        self._apply_style()  # — Aplica temas/estilos
        self._build_ui()  # — Constrói a interface

    def _apply_style(self):
        style = ttk.Style()  # — Objeto de estilo do ttk
        available_themes = style.theme_names()  # — Lista temas disponíveis
        
        if 'clam' in available_themes:
            style.theme_use('clam')  # — Usa tema 'clam' se disponível
        elif 'alt' in available_themes:
            style.theme_use('alt')  # — Caso contrário tenta 'alt'
        
        self.text_bg = '#FFFFFF'  # — Cor de fundo para a área de texto
        self.text_fg = '#333333'  # — Cor do texto
        self.font_family = 'Segoe UI' if 'Segoe UI' in font.families() else 'Helvetica'  # — Fonte preferida
        self.font_size = 11  # — Tamanho de fonte padrão
        
        style.configure('TButton', font=(self.font_family, self.font_size, 'bold'), padding=6)  # — Estilo de botão
        style.map('TButton', background=[('active', '#E1E1E1')])  # — Mapeamento visual ao ativar
        style.configure('TLabel', font=(self.font_family, self.font_size, 'bold'), foreground='#333333')  # — Estilo label
        style.configure('TEntry', font=(self.font_family, self.font_size), padding=5)  # — Estilo entrada de texto

    def _build_ui(self):
        self.master.title('Mini Navegador Web (Tkinter)')  # — Título da janela
        self.master.geometry('800x600')  # — Tamanho inicial da janela
        
        self.columnconfigure(0, weight=1)  # — Configura grid para expansão horizontal
        self.rowconfigure(1, weight=1)  # — Garante que a área de visualização cresça verticalmente

        # 1. Barra de Endereços (URL Bar)
        url_frame = ttk.Frame(self, padding="10 10 10 5")  # — Frame para agrupar elementos da URL bar
        url_frame.grid(row=0, column=0, sticky='ew')
        url_frame.columnconfigure(1, weight=1)  # — Coluna 1 (entrada) expande

        lbl = ttk.Label(url_frame, text='URL:', style='TLabel')  # — Rótulo "URL:"
        lbl.grid(row=0, column=0, sticky='w', padx=(0, 5))
        
        self.url_entry = ttk.Entry(url_frame, style='TEntry')  # — Campo de entrada para a URL
        self.url_entry.grid(row=0, column=1, sticky='ew')
        self.url_entry.insert(0, "https://www.w3schools.com/w3css/tryw3css_templates_gourmet_catering.htm") # URL de exemplo
        self.url_entry.bind('<Return>', lambda event: self.load_url())  # — Pressionar Enter carrega a URL
        
        go_btn = ttk.Button(url_frame, text='Ir', command=self.load_url, style='TButton')  # — Botão 'Ir'
        go_btn.grid(row=0, column=2, sticky='e', padx=(5, 0))
        
        local_html_btn = ttk.Button(url_frame, text='HTML Local', command=self.show_local_html_input, style='TButton')  # — Botão para injetar HTML local
        local_html_btn.grid(row=0, column=3, sticky='e', padx=(5, 0))

        # 2. Área de Visualização (Output)
        output_frame = ttk.Frame(self, padding="10 5 10 10")  # — Frame que contém o Text de saída e scrollbar
        output_frame.grid(row=1, column=0, sticky='nsew')
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        output_scroll = ttk.Scrollbar(output_frame)  # — Scrollbar vertical para a área de visualização
        output_scroll.grid(row=0, column=1, sticky='ns')
        
        self.output_text = tk.Text(output_frame, 
                                   wrap='word', 
                                   font=(self.font_family, self.font_size), 
                                   bg=self.text_bg, 
                                   fg=self.text_fg, 
                                   yscrollcommand=output_scroll.set,
                                   relief=tk.FLAT,
                                   padx=10, pady=10,
                                   state=tk.DISABLED) # Desabilitar edição para o usuário
        self.output_text.grid(row=0, column=0, sticky='nsew')
        output_scroll.config(command=self.output_text.yview)  # — Vincula scrollbar ao Text
        
        # Configuração das Tags de Estilo
        self._configure_tags()

    def show_local_html_input(self):
        """Abre uma nova janela para injetar HTML localmente."""
        
        # Cria a nova janela
        top = tk.Toplevel(self.master)  # — Janela filha para entrada de HTML
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
            html_content = input_text.get('1.0', tk.END)  # — Lê todo HTML inserido
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
        input_text.insert('1.0', sample)  # — Insere o HTML de exemplo na área de entrada

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

    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)  # — Tornar Text editável temporariamente
        self.output_text.delete('1.0', tk.END)  # — Limpa todo o conteúdo
        # Limpar referências de imagem
        parser = getattr(self, 'last_parser', None)
        if parser:
            parser.image_refs = []  # — Remove referências para liberar memória
        self.output_text.config(state=tk.DISABLED)  # — Volta a bloquear a edição

    def load_url(self):
        url = self.url_entry.get()  # — Lê URL da entrada
        if not url:
            return  # — Nada a fazer se entrada vazia

        # Adicionar http:// se não houver protocolo
        if not url.startswith(('http://', 'https://', 'file://')):
            url = 'http://' + url  # — Assume http se protocolo ausente
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)  # — Atualiza campo com protocolo adicionado

        self.clear_output()
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"Carregando: {url}...\n\n")  # — Mensagem inicial
        self.output_text.config(state=tk.DISABLED)
        self.update_idletasks() # Força a atualização da interface

        try:
            # Faz a requisição HTTP
            response = requests.get(url, timeout=10)  # — Requisição com timeout de 10s
            response.raise_for_status() # Levanta exceção para códigos de status ruins (4xx ou 5xx)
            
            html_content = response.text  # — Conteúdo HTML obtido
            self.current_url = url  # — Atualiza URL corrente
            
            self.render_html(html_content, url)  # — Renderiza o HTML obtido na interface

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
            parser.feed(html_content)  # — Alimenta o parser com o HTML para renderização
        except Exception as e:
            self.output_text.insert(tk.END, f"\n[Erro durante a análise do HTML: {e}]")  # — Mensagem de erro na análise
        finally:
            parser.close()  # — Fecha parser (libera recursos internos)
            self.output_text.config(state=tk.DISABLED)  # — Bloqueia edição novamente
            self.output_text.yview_moveto(0) # Rola para o topo da visualização

    def show_error(self, title, message):
        self.clear_output()
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"--- {title} ---\n\n{message}\n")  # — Exibe mensagem de erro na área de visualização
        self.output_text.config(state=tk.DISABLED)
        messagebox.showerror(title, message)  # — Mostra caixa de diálogo de erro

def main():
    # Instalar requests se não estiver presente (para garantir que o código funcione)
    try:
        import requests
    except ImportError:
        print("O módulo 'requests' não está instalado. Instalando...")
        import subprocess
        try:
            subprocess.check_call(['pip3', 'install', 'requests'])  # — Tenta instalar via pip3
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

    root = tk.Tk()  # — Cria a janela principal do tkinter
    root.option_add('*tearOff', tk.FALSE)  # — Desabilita menus destacáveis por padrão
    app = MiniBrowser(master=root)  # — Instancia o aplicativo
    root.mainloop()  # — Inicia o loop principal da interface

if __name__ == '__main__':
    main()  # — Executa main() quando o script for executado diretamente
