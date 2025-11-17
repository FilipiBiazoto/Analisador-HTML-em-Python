"""
Um renderizador simples de HTML para Tkinter.
Suporta: <p>, <br>, <b>/<strong>, <i>/<em>, <u>, <h1>-<h6>, <a href>, <ul>, <ol>, <li>, <img src>

Como usar: python analisadorhtml.py
Cole o HTML à esquerda e clique em "Renderizar".

Dependências opcionais:
- Pillow (para carregar imagens): pip install pillow

Observação: este não é um navegador completo. É uma aproximação para mostrar conteúdo básico.

""" 
# — Docstring no topo do arquivo explicando o propósito do script e instruções de uso.

from html.parser import HTMLParser
# — Importa a classe HTMLParser da biblioteca padrão para analisar HTML simples.

import tkinter as tk
# — Importa tkinter com o alias 'tk' para construção da interface gráfica.

from tkinter import ttk
# — Importa ttk (widgets temáticos do tkinter) para controles com aparência moderna.

from tkinter import font
# — Importa o módulo font do tkinter para consultar e definir fontes.

import webbrowser
# — Importa webbrowser para abrir links (URLs) no navegador do usuário.

import io
# — Importa io (não usado no código atual — pode ser utilidade futura para buffers de imagem/texto).
#    (Observação: io está importado mas não utilizado explicitamente no código.)

try:
    from PIL import Image, ImageTk
    # Definir um filtro de redimensionamento de alta qualidade se Pillow estiver disponível
    Image.ANTIALIAS = Image.Resampling.LANCZOS # Usar LANCZOS para melhor qualidade
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False
# — Tenta importar Pillow (PIL). Se disponível, define um filtro de redimensionamento de alta qualidade
#    (LANCZOS) e marca PIL_AVAILABLE True; caso contrário, marca False.
#    Observação: atribuir Image.ANTIALIAS pode ser redundante em versões mais recentes do Pillow,
#    mas aqui força um alias para usar Resampling.LANCZOS.

class SimpleHTMLParser(HTMLParser):
    def __init__(self, text_widget):
        super().__init__()
        self.text = text_widget
        self.tag_stack = []
        self.list_stack = []
        self.href = None
        self.image_refs = []  
    # — Classe que estende HTMLParser para transformar elementos HTML em conteúdo dentro de um Text widget.
    #    __init__: recebe o Text widget onde o conteúdo será inserido e inicializa estruturas auxiliares:
    #    - tag_stack: pilha para rastrear estilos/elementos abertos (negrito, itálico, cabeçalho, etc.)
    #    - list_stack: pilha para rastrear listas aninhadas (ul/ol) e índices de ol
    #    - href: URL atual quando dentro de <a>
    #    - image_refs: lista para manter referências das imagens (evitar coleta pelo GC)

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
            self.text.insert(tk.END, '\n') # Linha em branco antes da lista
            self.list_stack.append(('ul', None))
        elif tag == 'ol':
            self.text.insert(tk.END, '\n') # Linha em branco antes da lista
            self.list_stack.append(('ol', 1))
        elif tag == 'li':
            # Inserir quebra de linha antes de cada item de lista, exceto o primeiro
            if self.text.index(tk.END) != '1.0' and self.text.get(f'{self.text.index(tk.END)} -1c') != '\n':
                self.text.insert(tk.END, '\n')
                
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
    # — handle_starttag: chamado quando um tag de abertura é encontrado.
    #    - Converte attrs para dict.
    #    - Para tags de estilo (b, i, u) empilha um marcador na tag_stack.
    #    - Para cabeçalhos empilha o nome do tag (h1..h6) e insere uma quebra de linha antes.
    #    - <br> insere quebra de linha.
    #    - <p> insere quebra de linha e empilha 'p' (p pode aplicar espaçamento depois).
    #    - <a> guarda href em self.href e empilha 'link'.
    #    - <ul>/<ol> inserem linha em branco e empilham na list_stack; ol começa com índice 1.
    #    - <li> prepara marcador (bullet ou número), insere quebra de linha quando apropriado, insere o marcador
    #      e empilha 'li'.
    #    - <img>: obtém src e chama método de inserção de imagem se src presente.

    def handle_endtag(self, tag):
        if tag in ('b','strong','i','em','u','p','li'):
            style_map = {
                'b':'bold','strong':'bold','i':'italic','em':'italic','u':'underline','p':'p','li':'li'
            }
            style = style_map.get(tag)
            # Remove a tag correspondente da pilha
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i] == style:
                    del self.tag_stack[i]
                    break
        elif tag in ('h1','h2','h3','h4','h5','h6'):
            # Remove a tag de cabeçalho da pilha
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i] == tag:
                    del self.tag_stack[i]
                    break
            self.text.insert(tk.END, '\n')
        elif tag == 'a':
            # Remove a tag 'link' da pilha
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i] == 'link':
                    del self.tag_stack[i]
                    break
            self.href = None
        elif tag in ('ul','ol'):
            if self.list_stack:
                self.list_stack.pop()
            self.text.insert(tk.END, '\n') # Linha em branco depois da lista
    # — handle_endtag: chamado quando encontra um fechamento de tag.
    #    - Para tags de estilo e estrutura, procura na pilha a entrada correspondente e remove (do fim para o início).
    #    - Para cabeçalhos, remove o marcador e insere uma quebra de linha após o cabeçalho.
    #    - Para 'a', remove a tag 'link' e zera self.href.
    #    - Para listas, desempilha list_stack e adiciona linha em branco após a lista.

    def handle_data(self, data):
        # A lógica de HTMLParser pode dividir o texto em pedaços.
        # Para preservar o espaçamento, vamos inserir o 'data' original,
        # mas remover espaços em branco iniciais/finais se já houver um espaço ou quebra de linha.
        
        if not data:
            return

        # Normalizar múltiplos espaços em branco para um único espaço
        normalized_data = ' '.join(data.split())
        if not normalized_data:
            return

        # Tenta evitar espaços duplicados no início
        if self.text.index(tk.END) != '1.0':
            last_char = self.text.get(f'{self.text.index(tk.END)} -1c')
            if last_char not in ('\n', ' ') and data.startswith(' '):
                # Se o último caractere não for espaço/quebra de linha e o novo dado começar com espaço,
                # adicionamos um espaço antes do texto normalizado.
                normalized_data = ' ' + normalized_data
            elif last_char == ' ' and data.startswith(' '):
                # Se o último caractere for espaço e o novo dado começar com espaço, removemos o espaço inicial.
                normalized_data = normalized_data.lstrip()
        
        start_index = self.text.index(tk.END)
        self.text.insert(tk.END, normalized_data)
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
                # Cria uma tag única para o link
                tag_name = f'link_{start_index.replace(".","_")}'
                self.text.tag_add(tag_name, start_index, end_index)
                
                # Cria uma função wrapper para o evento de clique
                def open_link(event, url=self.href):
                    webbrowser.open(url)
                
                self.text.tag_bind(tag_name, '<Button-1>', open_link)
                self.text.tag_config(tag_name, foreground='#0078D7', underline=1) # Cor azul moderna
    # — handle_data: chamado para cada trecho de texto entre tags.
    #    - Normaliza espaços (colapsa múltiplos espaços em um único).
    #    - Previne duplicação de espaços dependendo do último caractere no Text widget.
    #    - Insere o texto no widget de saída e recupera índices iniciais e finais para aplicar tags de estilo.
    #    - Para cada marcador em tag_stack aplica a tag correspondente no intervalo inserido.
    #    - Para links (<a href>): cria uma tag única (para evitar conflitos) que:
    #         * associa um evento de clique para abrir URL no navegador,
    #         * configura estilo visual (cor e sublinhado).
    #    Observação: usar closures aqui captura self.href atual; como estamos criando tag por trecho,
    #    passamos url=self.href como default para fixar o valor naquele momento.

    def _insert_image(self, src):
        try:
            if src.startswith('http://') or src.startswith('https://'):
                raise ValueError('Carregamento por URL não suportado neste demo. Use caminho local.')
            
            if PIL_AVAILABLE:
                img = Image.open(src)
                # Redimensionamento para caber na área de visualização
                maxw, maxh = 400, 400
                w, h = img.size
                ratio = min(1, maxw/w, maxh/h)
                if ratio < 1:
                    # Usar o filtro de alta qualidade definido no início
                    img = img.resize((int(w*ratio), int(h*ratio)))
                photo = ImageTk.PhotoImage(img)
            else:
                # Fallback para tk.PhotoImage (suporta menos formatos)
                photo = tk.PhotoImage(file=src)
            
            # Manter uma referência para evitar que o garbage collector a remova
            self.image_refs.append(photo)
            self.text.image_create(tk.END, image=photo)
            self.text.insert(tk.END, '\n')
        except Exception as e:
            self.text.insert(tk.END, f'[Erro ao carregar imagem: {e}]\n')
    # — _insert_image: método auxiliar para inserir imagem local no Text widget.
    #    - Rejeita URLs remotos (levanta ValueError).
    #    - Se Pillow disponível: abre imagem, calcula ratio para limitar dentro de maxw/maxh,
    #      redimensiona com filtro de alta qualidade, converte para ImageTk.PhotoImage.
    #    - Se Pillow ausente: usa tk.PhotoImage (suporta GIF/PNG limitados).
    #    - Armazena referência em self.image_refs para evitar coleta pelo GC.
    #    - Insere a imagem no Text widget com image_create e adiciona quebra de linha após.
    #    - Em caso de erro insere uma mensagem de erro no Text widget.

class HTMLViewer(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=True)
        self._apply_style()
        self._build_ui()
    # — Classe que representa a interface gráfica do renderizador.
    #    __init__: configura o frame principal, empacota para preencher a janela e chama métodos
    #    para aplicar estilo e construir a interface.

    def _apply_style(self):
        # Tenta aplicar um tema moderno se disponível
        style = ttk.Style()
        available_themes = style.theme_names()
        
        # Preferir 'clam' ou 'alt' para um visual mais limpo que o padrão 'classic'
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')
        
        # Configurações de estilo para o Text Widget (que não é um widget ttk)
        self.text_bg = '#FFFFFF' # Fundo branco
        self.text_fg = '#333333' # Texto cinza escuro para melhor leitura
        self.font_family = 'Segoe UI' if 'Segoe UI' in font.families() else 'Helvetica'
        self.font_size = 11
        
        # Estilo para os botões
        style.configure('TButton', font=(self.font_family, self.font_size, 'bold'), padding=6)
        style.map('TButton', background=[('active', '#E1E1E1')])
        
        # Estilo para os Labels
        style.configure('TLabel', font=(self.font_family, self.font_size, 'bold'), foreground='#333333')
    # — _apply_style: busca aplicar tema ttk preferencialmente 'clam' ou 'alt',
    #    define cores, fonte e estilos de botão/label. Seleciona 'Segoe UI' se disponível,
    #    senão usa 'Helvetica'. Define tamanhos e mapeamento visual para botões e labels.

    def _build_ui(self):
        self.master.title('Renderizador HTML Simples (Tkinter) - Visualização Aprimorada')
        self.master.geometry('1200x800') # Aumentar o tamanho inicial da janela
        
        # Configurar o grid principal para expansão
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Usar Panedwindow para redimensionamento flexível
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky='nsew', padx=10, pady=10) # Adicionar padding externo

        # Frame da Esquerda (Entrada HTML)
        left = ttk.Frame(paned, padding="10 10 5 10")
        paned.add(left, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        lbl = ttk.Label(left, text='HTML de Entrada:', style='TLabel')
        lbl.grid(row=0, column=0, sticky='nw', pady=(0, 5))
        
        # Adicionar Scrollbar ao Text Widget de entrada
        input_frame = ttk.Frame(left)
        input_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)
        
        input_scroll = ttk.Scrollbar(input_frame)
        input_scroll.grid(row=0, column=1, sticky='ns')
        
        self.input_text = tk.Text(input_frame, 
                                  wrap='word', 
                                  font=(self.font_family, self.font_size), 
                                  bg=self.text_bg, 
                                  fg=self.text_fg, 
                                  yscrollcommand=input_scroll.set,
                                  relief=tk.FLAT, # Remover borda padrão
                                  padx=5, pady=5)
        self.input_text.grid(row=0, column=0, sticky='nsew')
        input_scroll.config(command=self.input_text.yview)
    # — Bloco que constrói a coluna esquerda da janela:
    #    - Título 'HTML de Entrada'
    #    - Frame com Text widget para inserir/colar HTML e scrollbar vertical associada.
    #    - Configurações do Text: wrap='word', fonte definida, cores, sem borda e padding interno.

        # Frame dos Botões
        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=2, column=0, sticky='ew', pady=(0, 5))
        
        render_btn = ttk.Button(btn_frame, text='Renderizar', command=self.render_html, style='TButton')
        render_btn.pack(side=tk.LEFT)
        
        clear_btn = ttk.Button(btn_frame, text='Limpar Saída', command=self.clear_output, style='TButton')
        clear_btn.pack(side=tk.LEFT, padx=10)
    # — Bloco de botões abaixo do Text de entrada:
    #    - Botão 'Renderizar' chama self.render_html
    #    - Botão 'Limpar Saída' chama self.clear_output

        # Frame da Direita (Visualização)
        right = ttk.Frame(paned, padding="10 10 10 10")
        paned.add(right, weight=2)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        lbl2 = ttk.Label(right, text='Visualização:', style='TLabel')
        lbl2.grid(row=0, column=0, sticky='nw', pady=(0, 5))

        # Adicionar Scrollbar ao Text Widget de saída
        output_frame = ttk.Frame(right)
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
                                   relief=tk.FLAT, # Remover borda padrão
                                   padx=10, pady=10) # Aumentar padding interno para melhor visualização
        self.output_text.grid(row=0, column=0, sticky='nsew')
        output_scroll.config(command=self.output_text.yview)
    # — Bloco que constrói a coluna direita (visualização):
    #    - Label 'Visualização'
    #    - Text widget de saída com scrollbar ligada, padding maior para leitura.
    #    - PanedWindow configurada com weight maior para a direita (mais espaço).

        # Configuração das Tags de Estilo
        
        # Estilos básicos
        self.output_text.tag_config('bold', font=(self.font_family, self.font_size, 'bold'))
        self.output_text.tag_config('italic', font=(self.font_family, self.font_size, 'italic'))
        self.output_text.tag_config('underline', underline=1)

        # Estilos de cabeçalho
        base_family = self.font_family
        self.output_text.tag_config('h1', font=(base_family, 24, 'bold'), spacing3=10) # spacing3 adiciona espaço após o parágrafo
        self.output_text.tag_config('h2', font=(base_family, 18, 'bold'), spacing3=8)
        self.output_text.tag_config('h3', font=(base_family, 14, 'bold'), spacing3=6)
        self.output_text.tag_config('h4', font=(base_family, 12, 'bold'), spacing3=4)
        self.output_text.tag_config('h5', font=(base_family, 11, 'bold'), spacing3=2)
        self.output_text.tag_config('h6', font=(base_family, 10, 'bold'), spacing3=2)
        
        # Estilo para parágrafo (adicionar um pouco de espaço)
        self.output_text.tag_config('p', spacing3=5)
    # — Define as tags (estilos) que serão aplicadas no Text de saída:
    #    - 'bold', 'italic', 'underline' para estilos inline.
    #    - 'h1'..'h6' com tamanhos e espaçamento posterior (spacing3).
    #    - 'p' apenas com espaçamento após.
    #    Observação: o Text widget aplica estilos por tags; as tags são adicionadas durante a análise.

    def clear_output(self):
        self.output_text.delete('1.0', tk.END)
        # Limpar referências de imagem para liberar memória
        parser = getattr(self, 'last_parser', None)
        if parser:
            parser.image_refs = []
    # — clear_output: apaga todo conteúdo do Text de saída e limpa referências de imagens
    #    do último parser armazenado (ajuda a liberar memória).

    def render_html(self):
        html = self.input_text.get('1.0', tk.END)
        self.clear_output()
        # Cria e armazena o parser para manter as referências de imagem
        parser = SimpleHTMLParser(self.output_text)
        self.last_parser = parser
        parser.feed(html)
        parser.close()
    # — render_html: chamado ao clicar em "Renderizar".
    #    - Lê todo o conteúdo do Text de entrada,
    #    - Limpa saída anterior,
    #    - Cria um SimpleHTMLParser ligado ao Text de saída, armazena em self.last_parser,
    #    - Alimenta (feed) o parser com o HTML e fecha o parser.

def main():
    root = tk.Tk()
    # Configurar o estilo da janela principal para um visual mais moderno
    root.option_add('*tearOff', tk.FALSE) # Desabilitar menus destacáveis
    
    app = HTMLViewer(master=root)
    
    # Exemplo de HTML mais completo
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
<img src="foto.png">
'''
    app.input_text.insert('1.0', sample)
    root.mainloop()
# — main(): cria a janela root Tk, define uma opção (desabilita menus "tearOff"),
#    instancia HTMLViewer com master=root, injeta um exemplo de HTML na área de entrada
#    (sample) para demonstração, e inicia o loop principal com root.mainloop().

if __name__ == '__main__':
    main()
# — Padrão Python para executar main() somente quando o script for executado diretamente.
