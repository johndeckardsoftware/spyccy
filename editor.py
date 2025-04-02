
import os, re
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from hashlib import md5
import app_globals
from config import Config, STYLE_TAG
import basic2tape

class Notebook(ttk.Notebook):
    def __init__(self, *args):
        ttk.Notebook.__init__(self, *args)
        self.enable_traversal()
        self.pack(expand=1, fill="both")
        self.bind("<B1-Motion>", self.move_tab)

    # Get the object of the current tab.
    def current_tab(self):
        return self.nametowidget( self.select() )

    def indexed_tab(self, index):
        return self.nametowidget( self.tabs()[index] )

    # Move tab position by dragging tab
    def move_tab(self, event):
        '''
        Check if there is more than one tab.

        Use the y-coordinate of the current tab so that if the user moves the mouse up / down
        out of the range of the tabs, the left / right movement still moves the tab.
        '''
        if self.index("end") > 1:
            y = self.current_tab().winfo_y() - 5

            try:
                self.insert( min( event.widget.index('@%d,%d' % (event.x, y)), self.index('end')-2), self.select() )
            except tk.TclError:
                pass

class Tab(ttk.Frame):
    def __init__(self, *args, editor, FileDir):
        ttk.Frame.__init__(self, *args)
        self.editor = editor
        self.status_bar = None
        self.textbox = self.create_text_widget()

        # configure syntax highlight
        self.regexp = re.compile(r'\w+|"(?:[^"\\]|\\.)*"|\s*#')
        self.tags = [
                (STYLE_TAG.TOKEN, "#266ce6"),
                (STYLE_TAG.NUMBER, "#d32f2f"),
                (STYLE_TAG.STRING, "#f57c00"),
                (STYLE_TAG.COMMENT, "#3aa925")
            ]
        for tag in self.tags:
            self.textbox.tag_config(tag[0], foreground=tag[1])
        self.textbox.tag_configure("sel", background="#D6E8F8")

        self.file_dir = None
        self.file_name = os.path.basename(FileDir)
        self.status = md5(self.textbox.get(1.0, 'end').encode('utf-8'))

    def create_text_widget(self):
        #Add the status bar
        self.status_bar = tk.Label(self, text="", padx=5, relief="ridge", fg='white', bg="blue", anchor='w')
        self.status_bar.pack(side='bottom', fill='x')

        # Horizontal Scroll Bar
        xscrollbar = tk.Scrollbar(self, orient='horizontal')
        xscrollbar.pack(side='bottom', fill='x')

        # Vertical Scroll Bar
        yscrollbar = tk.Scrollbar(self)
        yscrollbar.pack(side='right', fill='y')

        # Create Text Editor Box
        #textbox = tk.Text(self, relief='sunken', borderwidth=0, wrap='none', background='black', foreground='white', insertbackground='white')
        textbox = tk.Text(self, relief='sunken', borderwidth=0, wrap='none')
        textbox.configure(xscrollcommand=xscrollbar.set, yscrollcommand=yscrollbar.set, undo=True, autoseparators=True)

        # Pack the textbox
        textbox.pack(fill='both', expand=True)

        # Configure Scrollbars
        xscrollbar.configure(command=textbox.xview)
        yscrollbar.configure(command=textbox.yview)

        return textbox

class Editor:
    def __init__(self, top_level, parent, file=None, text=None):
        self.master = top_level
        self.parent = parent
        self.master.title("SPYCCY - Editor")
        self.master.geometry(Config.get('app.editor.geometry', '640x500'))
        self.frame = tk.Frame(self.master)
        self.frame.pack()
        self.master.iconphoto(False, app_globals.APP_ICON)
        self.filetypes = (("Normal text file", "*.txt *.bas"), ("all files", "*.*"))
        self.init_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.untitled_count = 1

        self.vars = {}
        name = 'app.editor.syntax_highligth'
        self.vars[name] = tk.BooleanVar(value=Config.get(name, True), name=name)
        self.vars[name].trace_add("write", callback=self.var_callback)

        # Create Notebook ( for tabs )
        self.nb = Notebook(self.master)
        self.nb.bind("<Button-2>", self.close_tab)
        self.nb.bind('<<NotebookTabChanged>>', self.tab_change)
        self.nb.bind('<Button-3>', self.right_click_tab)

        # Override the X button.
        self.master.protocol('WM_DELETE_WINDOW', self.exit)

        # Menu Bar
        menubar = tk.Menu(self.master)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_as)
        file_menu.add_command(label="Close", command=self.close_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=self.cut)
        edit_menu.add_command(label="Copy", command=self.copy)
        edit_menu.add_command(label="Paste", command=self.paste)
        edit_menu.add_command(label="Delete", command=self.delete)
        edit_menu.add_command(label="Select All", command=self.select_all)

        # Format Menu
        format_menu = tk.Menu(menubar, tearoff=0)
        self.word_wrap = tk.BooleanVar()
        format_menu.add_checkbutton(label="Word Wrap", onvalue=True, offvalue=False, variable=self.word_wrap, command=self.wrap)
        format_menu.add_separator()
        format_menu.add_checkbutton(label="Syntax highlight", onvalue=True, offvalue=False, variable=self.vars['app.editor.syntax_highligth'],
                                     command=self.set_syntax_highlight)

        # zmakebas Menu
        zmake_menu = tk.Menu(menubar, tearoff=0)
        zmake_menu.add_command(label="Run", command=self.run_zmakebas)

        # zxbasic Menu
        zxbasic_menu = tk.Menu(menubar, tearoff=0)
        zxbasic_menu.add_command(label="Compile and Run", command=self.run_zxbasic)
        zxbasic_menu.add_command(label="Show assembly", command=self.run_zxasm)

        # Attach to Menu Bar
        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        menubar.add_cascade(label="Format", menu=format_menu)
        menubar.add_cascade(label="ZMakebas", menu=zmake_menu)
        menubar.add_cascade(label="ZXBASIC", menu=zxbasic_menu)

        self.master.configure(menu=menubar)

        # Create right-click menu.
        self.right_click_menu = tk.Menu(self.master, tearoff=0)
        self.right_click_menu.add_command(label="Undo", command=self.undo)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="Cut", command=self.cut)
        self.right_click_menu.add_command(label="Copy", command=self.copy)
        self.right_click_menu.add_command(label="Paste", command=self.paste)
        self.right_click_menu.add_command(label="Delete", command=self.delete)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="Select All", command=self.select_all)

        # Create tab right-click menu
        self.tab_right_click_menu = tk.Menu(self.nb, tearoff=0)
        self.tab_right_click_menu.add_command(label="New Tab", command=self.new_file)

        # Keyboard / Click Bindings
        self.master.bind_class('Text', '<Control-s>', self.save_file)
        self.master.bind_class('Text', '<Control-o>', self.open_file)
        self.master.bind_class('Text', '<Control-n>', self.new_file)
        self.master.bind_class('Text', '<Control-a>', self.select_all)
        self.master.bind_class('Text', '<Control-w>', self.close_tab)
        self.master.bind_class('Text', '<Button-3>', self.right_click)

        #All below bindings are 1 position behind
        self.master.bind("<Button 1>", self.update_status_bar)
        self.master.bind("<Key>", self.update_status_bar)

        self.master.bind('<Configure>', self.configure_callback)

        # Create initial tab and ' + ' tab
        if file:
            self.open_file(file_dir=file)
        elif text:
            self.open_text(text)
        else:
            self.nb.add(Tab(self.master, editor=self, FileDir='Untitled'), text='Untitled')
        self.set_syntax_highlight()
        self.nb.add(Tab(self.master, editor=self, FileDir='f'), text=' + ')

    def var_callback(self, var, index, mode):
        if mode == "write":
            (Config.set(var, self.vars[var].get()))

    def set_syntax_highlight(self):
        curr_tab = self.nb.current_tab()
        textbox = curr_tab.textbox
        # set syntax highlight for all document
        syntax_highlight = self.vars['app.editor.syntax_highligth'].get()
        self.syntax_highlight_all(syntax_highlight)
        # bind/unbind each key Release to the syntax_higlight function
        if syntax_highlight:
            textbox.bind("<KeyRelease>", lambda event: self.syntax_highlight())
        else:
            textbox.unbind("<KeyRelease>")

    def update_status_bar(self, event=None):
        # schedule an update after the key press is handled
        self.master.after(0, self._update_status_bar)

    def _update_status_bar(self):
        #Get cursor position
        curr_tab = self.nb.current_tab()
        cursor_pos =  curr_tab.textbox.index(tk.INSERT)
        rc = cursor_pos.split('.')
        curr_tab.status_bar.configure(text=f"Ln {rc[0]}, Col {rc[1]}")

    def configure_callback(self, event):
        Config.set('app.editor.geometry', self.master.geometry())

    def open_file(self, file_dir=None, *args):
        if not file_dir:
            # Open a window to browse to the file you would like to open, returns the directory.
            file_dir = filedialog.askopenfilename(initialdir=self.init_dir, title="Select file", filetypes=self.filetypes)

        # If directory is not the empty string, try to open the file.
        if file_dir:
            try:
                # Open the file.
                file = open(file_dir)

                # Create a new tab and insert at end.
                new_tab = Tab(self.master, editor=self, FileDir=file_dir)
                tab_index = self.nb.index('end')
                if tab_index > 1:
                    self.nb.insert( tab_index-1, new_tab, text=os.path.basename(file_dir))
                else:
                    self.nb.add(new_tab, text=os.path.basename(file_dir))
                self.nb.select( new_tab )

                # Puts the contents of the file into the text widget.
                self.nb.current_tab().textbox.insert('end', file.read())

                # Update hash
                self.nb.current_tab().status = md5(self.nb.current_tab().textbox.get(1.0, 'end').encode('utf-8'))
            except Exception as e:
                print(str(e))
                return

    def open_text(self, text):
        # Create a new tab and insert at end.
        new_tab = Tab(self.master, editor=self, FileDir='info')
        tab_index = self.nb.index('end')
        if tab_index > 1:
            self.nb.insert( tab_index-1, new_tab, text='info')
        else:
            self.nb.add(new_tab, text='info')
        self.nb.select( new_tab )
        self.nb.current_tab().textbox.insert('end', text)
        self.nb.current_tab().status = md5(self.nb.current_tab().textbox.get(1.0, 'end').encode('utf-8'))

    def save_as(self):
        curr_tab = self.nb.current_tab()

        # Gets file directory and name of file to save.
        file_dir = filedialog.asksaveasfilename(initialdir=self.init_dir, title="Select file", filetypes=self.filetypes)

        # Return if directory is still empty (user closes window without specifying file name).
        if not file_dir:
            return False

        # Adds .txt suffix if not already included.
        fil, ext = os.path.splitext(file_dir)
        if ext == '':
            file_dir += '.txt'

        curr_tab.file_dir = file_dir
        curr_tab.file_name = os.path.basename(file_dir)
        self.nb.tab( curr_tab, text=curr_tab.file_name)

        # Writes text widget's contents to file.
        file = open(file_dir, 'w', encoding="utf-8")
        file.write(curr_tab.textbox.get(1.0, 'end'))
        file.close()

        # Update hash
        curr_tab.status = md5(curr_tab.textbox.get(1.0, 'end').encode('utf-8'))

        return True

    def save_file(self, *args):
        curr_tab = self.nb.current_tab()

        # If file directory is empty or Untitled, use save_as to get save information from user.
        if not curr_tab.file_dir:
            return self.save_as()

        # Otherwise save file to directory, overwriting existing file or creating a new one.
        else:
            with open(curr_tab.file_dir, 'w') as file:
                file.write(curr_tab.textbox.get(1.0, 'end'))

            # Update hash
            curr_tab.status = md5(curr_tab.textbox.get(1.0, 'end').encode('utf-8'))

            return True

    def new_file(self, *args):
        # Create new tab
        new_tab = Tab(self.master, editor=self, FileDir=self.default_filename())
        new_tab.textbox.configure(wrap= 'word' if self.word_wrap.get() else 'none')
        self.nb.insert( self.nb.index('end')-1, new_tab, text=new_tab.file_name)
        self.nb.select( new_tab )

    def copy(self):
        # Clears the clipboard, copies selected contents.
        try:
            sel = self.nb.current_tab().textbox.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.master.clipboard_clear()
            self.master.clipboard_append(sel)
        # If no text is selected.
        except tk.TclError:
            pass

    def delete(self):
        # Delete the selected text.
        try:
            self.nb.current_tab().textbox.delete(tk.SEL_FIRST, tk.SEL_LAST)
        # If no text is selected.
        except tk.TclError:
            pass

    def cut(self):
        # Copies selection to the clipboard, then deletes selection.
        try:
            sel = self.nb.current_tab().textbox.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.master.clipboard_clear()
            self.master.clipboard_append(sel)
            self.nb.current_tab().textbox.delete(tk.SEL_FIRST, tk.SEL_LAST)
        # If no text is selected.
        except tk.TclError:
            pass

    def wrap(self):
        if self.word_wrap.get() == True:
            for i in range(self.nb.index('end')-1):
                self.nb.indexed_tab(i).textbox.configure(wrap="word")
        else:
            for i in range(self.nb.index('end')-1):
                self.nb.indexed_tab(i).textbox.configure(wrap="none")

    def paste(self):
        try:
            self.nb.current_tab().textbox.insert(tk.INSERT, self.master.clipboard_get())
        except tk.TclError:
            pass

    def select_all(self, *args):
        curr_tab = self.nb.current_tab()

        # Selects / highlights all the text.
        curr_tab.textbox.tag_add(tk.SEL, "1.0", tk.END)

        # Set mark position to the end and scroll to the end of selection.
        curr_tab.textbox.mark_set(tk.INSERT, tk.END)
        curr_tab.textbox.see(tk.INSERT)

    def undo(self):
        self.nb.current_tab().textbox.edit_undo()

    def right_click(self, event):
        self.right_click_menu.post(event.x_root, event.y_root)

    def right_click_tab(self, event):
        self.tab_right_click_menu.post(event.x_root, event.y_root)

    def close_tab(self, event=None):
        # Close the current tab if close is selected from file menu, or keyboard shortcut.
        if event is None or event.type == str( 2 ):
            selected_tab = self.nb.current_tab()
        # Otherwise close the tab based on coordinates of center-click.
        else:
            try:
                index = event.widget.index('@%d,%d' % (event.x, event.y))
                selected_tab = self.nb.indexed_tab( index )

                if index == self.nb.index('end')-1:
                    return False

            except tk.TclError:
                return False

        # Prompt to save changes before closing tab
        if self.save_changes(selected_tab):
            # if the tab next to '+' is selected, select the previous tab to prevent
            # automatically switching to '+' tab when current tab is closed
            if self.nb.index('current') > 0 and self.nb.select() == self.nb.tabs()[-2]:
                self.nb.select(self.nb.index('current')-1)
            self.nb.forget( selected_tab )
        else:
            return False

        # Exit if last tab is closed
        if self.nb.index("end") <= 1:
            if self.parent:
                self.parent.editor = None
            self.master.destroy()

        return True

    def exit(self):
        # Check if any changes have been made.
        for i in range(self.nb.index('end')-1):
            if self.close_tab() is False:
                break
        if self.parent:
            self.parent.editor = None

    def save_changes(self, tab):
        # Check if any changes have been made, returns False if user chooses to cancel rather than select to save or not.
        if md5(tab.textbox.get(1.0, 'end').encode('utf-8')).digest() != tab.status.digest():
            # Select the tab being closed is not the current tab, select it.
            if self.nb.current_tab() != tab:
                self.nb.select(tab)

            m = messagebox.askyesnocancel('Editor', 'Do you want to save changes to ' + tab.file_name + '?' )

            # If None, cancel.
            if m is None:
                return False
            # else if True, save.
            elif m is True:
                return self.save_file()
            # else don't save.
            else:
                pass

        return True

    def default_filename(self):
        self.untitled_count += 1
        return 'Untitled' + str(self.untitled_count-1)

    def tab_change(self, event):
        # If last tab was selected, create new tab
        if self.nb.select() == self.nb.tabs()[-1]:
            self.new_file()
        self.set_syntax_highlight()

    def run_zmakebas(self):
        curr_tab = self.nb.current_tab()
        temp_bas_file = './tmp/tmpzmake.bas'
        temp_tap_file = './tmp/tmpzmake.tap'
        file = open(temp_bas_file,"w")
        file.write(curr_tab.textbox.get(1.0, 'end'))
        file.close()
        ret = basic2tape.zmakebas(temp_bas_file, temp_tap_file)
        if ret and self.parent:
            self.parent.emulator.tape_load(temp_tap_file)
            os.remove(temp_bas_file)
            os.remove(temp_tap_file)
            self.parent.window.focus_force()

    def run_zxbasic(self):
        curr_tab = self.nb.current_tab()
        temp_bas_file = './tmp/tmpzxbc.bas'
        temp_tap_file = './tmp/tmpzxbc.tzx'
        file = open(temp_bas_file,"w")
        file.write(curr_tab.textbox.get(1.0, 'end'))
        file.close()
        ret, out_format, errors = basic2tape.zxbasic(temp_bas_file, temp_tap_file)
        if ret:
            self.open_text(errors)
        elif self.parent:
            self.parent.emulator.tape_load(temp_tap_file)
            os.remove(temp_bas_file)
            os.remove(temp_tap_file)
            self.parent.window.focus_force()

    def run_zxasm(self):
        curr_tab = self.nb.current_tab()
        temp_bas_file = './tmp/tmpzxbc.bas'
        temp_asm_file = './tmp/tmpzxbc.asm'
        file = open(temp_bas_file, "w", encoding="utf-8")
        file.write(curr_tab.textbox.get(1.0, 'end'))
        file.close()
        ret, out_format, errors = basic2tape.zxasm(temp_bas_file, temp_asm_file)
        if ret:
            self.open_text(errors)
        self.open_file(temp_asm_file)
        os.remove(temp_bas_file)
        os.remove(temp_asm_file)

    def syntax_highlight(self, start_index="insert linestart", end_index="insert lineend"):
        curr_tab = self.nb.current_tab()
        textbox = curr_tab.textbox
        # remove all tag instances
        for tag in curr_tab.tags:
            textbox.tag_remove(tag[0], start_index, end_index)
        # loop through each match and add the corresponding tag
        regexp = curr_tab.regexp
        text = textbox.get(start_index, end_index)
        for match in regexp.finditer(text):
            start, end = match.span()
            style_tag = self.get_style_tag(match.group())
            if style_tag:
                if style_tag == STYLE_TAG.COMMENT:
                    textbox.tag_add(style_tag, f"{start_index}+{start}c", end_index)
                    break
                else:
                    textbox.tag_add(style_tag, f"{start_index}+{start}c", f"{start_index}+{end}c")
        
        textbox.edit_modified(True)

    def get_style_tag(self, token):
        if not token:
            return None
        token = token.upper()
        if token == "REM" or token.startswith('#'):
            return STYLE_TAG.COMMENT
        elif token in basic2tape.TOKENS:
            return STYLE_TAG.TOKEN
        elif self.is_number(token):
            return STYLE_TAG.NUMBER
        elif token.startswith('"'):
            return STYLE_TAG.STRING
        return None

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def syntax_highlight_all(self, on_off):
        curr_tab = self.nb.current_tab()
        textbox = curr_tab.textbox
        numlines = int(textbox.index('end - 1 line').split('.')[0])
        for i in range(1, numlines+1):
            start_index=f'{i}.0'
            end_index=f'{i+1}.0'
            if on_off:
                self.syntax_highlight(start_index=start_index, end_index=end_index)
            else:
                for tag in curr_tab.tags:
                    textbox.tag_remove(tag[0], start_index, end_index)

def main():
    root = tk.Tk()
    app = Editor(root, None)
    root.mainloop()

if __name__ == '__main__':
    main()
