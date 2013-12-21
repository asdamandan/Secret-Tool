#!/usr/local/bin/python
# coding: utf-8

import wx, os, binascii, ConfigParser
from baseconv import *
from module_locator import *
from rom_insertion_operations import *

OPEN = 1
poke_num = 0
class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(800,600))
        self.open_rom = None
        self.rom_id = None
        self.path = module_path()
        self.open_rom_ini = {}
        
        self.panel = wx.Panel(self)
        self.tabbed_area = TabbedEditorArea(self.panel)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.tabbed_area, 1, wx.ALL|wx.EXPAND, 5)
        self.panel.SetSizer(self.sizer)
        self.Layout()
        
        self.CreateStatusBar() # A Statusbar in the bottom of the window

        # Setting up the menu.
        filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        filemenu.Append(OPEN, "&Open"," Open a ROM.")
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        
        self.Bind(wx.EVT_MENU, self.open_file, id=OPEN)
        
        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.Show(True)
        
    def open_file(self, *args):
        open_dialog = wx.FileDialog(self, message="Open a rom...", 
                                                        defaultDir=os.getcwd(), style=wx.OPEN)
        if open_dialog.ShowModal() == wx.ID_OK:
            filename = open_dialog.GetPath()
            self.open_rom = open(filename, "r+b")
            
            #Here we are going to check if the game has been opened before.
            #If yes, load it's custom ini. If no, create its ini.
            self.Config = ConfigParser.ConfigParser()
            ini = os.path.join(self.path,"PokeRoms.ini")
            self.Config.read(ini)
            if str(self.Config.get("ALL", "JustUseStandardIni")) == "True":
                game_code_offset = get_decimal_offset_from_hex_string("AC")
                self.open_rom.seek(game_code_offset, 0)
                self.rom_id = self.open_rom.read(4)
            
            else:
                rom_id_offset_hex = str(self.Config.get("ALL", "OffsetThatContainsSecondRomID"))
                rom_id_offset = get_decimal_offset_from_hex_string(rom_id_offset_hex)
                
                self.open_rom.seek(rom_id_offset) #Seek to last 2 bytes in rom
                self.rom_id = self.open_rom.read(2)
                self.rom_id = str(binascii.hexlify(self.rom_id)) 

                all_possible_rom_ids = self.Config.sections()
                
                if self.rom_id != "ffff":
                    if self.rom_id not in all_possible_rom_ids:
                        wx.MessageBox(
                        "At rom offset %s there is an unknown rom id. Please see documentation." %rom_id_offset_hex, 
                        'Error', 
                        wx.OK | wx.ICON_INFORMATION)
                    
                else:
                    game_code_offset = get_decimal_offset_from_hex_string("AC")
                    self.open_rom.seek(game_code_offset, 0)
                    game_code = self.open_rom.read(4)
                    self.open_rom.seek(rom_id_offset)
                    x = "0000"
                    y = None
                    while y == None:
                        if x in all_possible_rom_ids:
                            x = str(int(x) + 1)
                            if len(x) != 4:
                                n = 4 - len(x)
                                for n in range(n):
                                    x = "0"+x
                            continue
                        else:
                            self.rom_id = x
                            
                            #Write new rom_id to rom.
                            byte_rom_id = get_hex_from_string(self.rom_id)
                            self.open_rom.write(byte_rom_id)
                            
                            self.Config.add_section(self.rom_id)
                            options = self.Config.options(game_code)
                            tmp_ini = {}
                            for opt in options:
                                tmp_ini[opt] = self.Config.get(game_code, opt)
                                
                            for opt, value in tmp_ini.items():
                                self.Config.set(self.rom_id, opt, value)
                            with open(ini, "w") as PokeRomsIni:
                                self.Config.write(PokeRomsIni)
                            y = True
            self.reload_all_tabs()
            
    def reload_all_tabs(self):
        self.panel.Destroy()
        self.panel = wx.Panel(self)
        
        self.tabbed_area = TabbedEditorArea(self.panel)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.tabbed_area, 1, wx.ALL|wx.EXPAND, 5)
        self.panel.SetSizer(self.sizer)
        self.Layout()
        size = self.GetSize()
        self.SetSize((size[0]+1, size[1]+1))
        self.SetSize(size)


#############################################################
#This class is what holds all of the main tabs.
#############################################################
class TabbedEditorArea(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, id=wx.ID_ANY, style=
                                             wx.BK_DEFAULT
                                             #wx.BK_TOP 
                                             #wx.BK_BOTTOM
                                             #wx.BK_LEFT
                                             #wx.BK_RIGHT
                                             )
        
        PokeDataTab = PokemonDataEditor(self)
        self.AddPage(PokeDataTab, "Pokemon Data Editor")
        
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        
    def OnPageChanged(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        event.Skip()

    def OnPageChanging(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        event.Skip()

        
#############################################################
#This tab will allow editing of Pokemon Stats, moves, etc
#############################################################
class PokemonDataEditor(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        if 'frame' in globals():
            if frame.open_rom is not None:
                poke_names = self.get_pokemon_names()
                self.Pokes = wx.ComboBox(self, -1, choices=poke_names, 
                                value=poke_names[0],
                                style=wx.SUNKEN_BORDER,
                                pos=(0, 0), size=(200, 20))
                self.Pokes.Bind(wx.EVT_COMBOBOX, self.on_change_poke)
                global poke_num
                poke_num = 0
                
                self.sizer = wx.BoxSizer(wx.VERTICAL)
                self.sizer.Add(self.Pokes, 0, wx.ALL, 2)
                self.tabbed_area = DataEditingTabs(self)
                self.sizer.Add(self.tabbed_area, 1, wx.ALL|wx.EXPAND, 2)
                self.SetSizer(self.sizer)
        self.Layout()
        
    def get_pokemon_names(self):
        offset = frame.Config.get(frame.rom_id, "PokeNames")
        offset = get_decimal_offset_from_hex_string(offset)
        frame.open_rom.seek(offset, 0)
        number = int(frame.Config.get(frame.rom_id, "NumberofPokes"))
        name_length = int(frame.Config.get(frame.rom_id, "PokeNamesLength"), 16)
        names = [] 
        for num in range(number):
            tmp_name = frame.open_rom.read(name_length)
            tmp_name = convert_ascii_and_poke(tmp_name, "to_poke")
            name = tmp_name.split("\xff", 1)
            names.append(name[0])
        return names
    
    def on_change_poke(self, event):
        global poke_num
        poke_num = self.Pokes.GetSelection()
        self.tabbed_area.Destroy()
        self.tabbed_area = DataEditingTabs(self)
        self.sizer.Add(self.tabbed_area, 1, wx.ALL|wx.EXPAND, 2)
        self.Layout()
        
class DataEditingTabs(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, id=wx.ID_ANY, style=
                                             wx.BK_DEFAULT
                                             #wx.BK_TOP 
                                             #wx.BK_BOTTOM
                                             #wx.BK_LEFT
                                             #wx.BK_RIGHT
                                             )
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        stats = StatsTab(self)
        moves = MovesTab(self)
        evo = EvoTab(self)
        dex = PokeDexTab(self)
        
        self.AddPage(stats, "Stats")
        self.AddPage(moves, "Moves")
        self.AddPage(evo, "Evolutions")
        self.AddPage(dex, "PokeDex")
        
        self.SetSizer(sizer)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        
    def OnPageChanged(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        event.Skip()

    def OnPageChanging(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        event.Skip()
        
class StatsTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        self.sizer = wx.GridBagSizer(3,3)
        basestatsoffset = int(frame.Config.get(frame.rom_id, "pokebasestats"), 16)
        basestatslength = int(frame.Config.get(frame.rom_id, "pokebasestatslength"), 16)
        global poke_num
        basestatsoffset = basestatslength*poke_num + basestatsoffset
        frame.open_rom.seek(basestatsoffset, 0)
        self.base_stats_dict = {}
        self.basestats = frame.open_rom.read(basestatslength)
        self.sort_base_stats()
        self.generate_ui()
        
        self.SetSizer(self.sizer)
        self.Layout()
        
    def generate_ui(self):
        #----------Set up a panel for the regular stats.----------#
        basic_stats = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        basic_stats_sizer = wx.GridBagSizer(3,3)
        
        basic_stats_txt = wx.StaticText(basic_stats, -1,"Base Stats:")
        basic_stats_sizer.Add(basic_stats_txt, (0, 0), (1,2), wx.EXPAND)
        
        HP_txt = wx.StaticText(basic_stats, -1,"HP:")
        basic_stats_sizer.Add(HP_txt, (1, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.HP = wx.TextCtrl(basic_stats, -1,style=wx.TE_CENTRE, size=(40,-1))
        basic_stats_sizer.Add(self.HP,(1, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        ATK_txt = wx.StaticText(basic_stats, -1,"ATK:")
        basic_stats_sizer.Add(ATK_txt, (2, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.ATK = wx.TextCtrl(basic_stats, -1,style=wx.TE_CENTRE, size=(40,-1))
        basic_stats_sizer.Add(self.ATK,(2, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        DEF_txt = wx.StaticText(basic_stats, -1,"DEF:")
        basic_stats_sizer.Add(DEF_txt, (3, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.DEF = wx.TextCtrl(basic_stats, -1,style=wx.TE_CENTRE, size=(40,-1))
        basic_stats_sizer.Add(self.DEF,(3, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        SPD_txt = wx.StaticText(basic_stats, -1,"SPD:")
        basic_stats_sizer.Add(SPD_txt, (4, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.SPD = wx.TextCtrl(basic_stats, -1,style=wx.TE_CENTRE, size=(40,-1))
        basic_stats_sizer.Add(self.SPD,(4, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        SpATK_txt = wx.StaticText(basic_stats, -1,"Sp. ATK:")
        basic_stats_sizer.Add(SpATK_txt, (5, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.SpATK = wx.TextCtrl(basic_stats, -1,style=wx.TE_CENTRE, size=(40,-1))
        basic_stats_sizer.Add(self.SpATK,(5, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        SpDEF_txt = wx.StaticText(basic_stats, -1,"Sp. DEF:")
        basic_stats_sizer.Add(SpDEF_txt, (6, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.SpDEF = wx.TextCtrl(basic_stats, -1,style=wx.TE_CENTRE, size=(40,-1))
        basic_stats_sizer.Add(self.SpDEF,(6, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        basic_stats_sizer.SetFlexibleDirection(wx.BOTH)
        
        basic_stats.SetSizerAndFit(basic_stats_sizer)
        self.sizer.Add(basic_stats, (0,0), wx.DefaultSpan,  wx.ALL, 2)
        
        #---------Set up a panel for Types----------#
        types = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        types_sizer = wx.GridBagSizer(3,3)
        
        #Get list of types:
        t_offset = int(frame.Config.get(frame.rom_id, "TypeNames"), 16)
        t_name_length = int(frame.Config.get(frame.rom_id, "TypeNamesLength"), 16)
        t_number = int(frame.Config.get(frame.rom_id, "NumberofTypes"))
        list_of_types = []
        
        frame.open_rom.seek(t_offset, 0)
        for n in range(t_number):
            temp_type = frame.open_rom.read(t_name_length)
            temp_type = convert_ascii_and_poke(temp_type, "to_poke")
            temp_type = temp_type.split("\xff")
            list_of_types.append(temp_type[0])
        
        TYPE1_txt = wx.StaticText(types, -1,"Type 1:")
        types_sizer.Add(TYPE1_txt, (0, 0), wx.DefaultSpan,  wx.ALL, 4)
        self.TYPE1 = wx.ComboBox(types, -1, choices=list_of_types,
                                style=wx.SUNKEN_BORDER, size=(80, 20))
        types_sizer.Add(self.TYPE1, (0, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        TYPE2_txt = wx.StaticText(types, -1,"Type 2:")
        types_sizer.Add(TYPE2_txt, (1, 0), wx.DefaultSpan,  wx.ALL, 4)
        self.TYPE2 = wx.ComboBox(types, -1, choices=list_of_types,
                                style=wx.SUNKEN_BORDER, size=(80, 20))
        types_sizer.Add(self.TYPE2, (1, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        types.SetSizerAndFit(types_sizer)
        self.sizer.Add(types, (1,0), wx.DefaultSpan,  wx.ALL, 2)
        
        #----------Set up a panel for Catch Rate and Base EXP----------#
        catch_rate_base_exp = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        catch_rate_base_exp_sizer = wx.GridBagSizer(3,3)
        
        CATCHRATE_txt = wx.StaticText(catch_rate_base_exp, -1,"Catch Rate:")
        catch_rate_base_exp_sizer.Add(CATCHRATE_txt, (0, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.CATCHRATE = wx.TextCtrl(catch_rate_base_exp, -1,style=wx.TE_CENTRE, size=(40,-1))
        catch_rate_base_exp_sizer.Add(self.CATCHRATE,(0, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        BASEEXP_txt = wx.StaticText(catch_rate_base_exp, -1,"Base Exp:")
        catch_rate_base_exp_sizer.Add(BASEEXP_txt, (1, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.BASEEXP = wx.TextCtrl(catch_rate_base_exp, -1,style=wx.TE_CENTRE, size=(40,-1))
        catch_rate_base_exp_sizer.Add(self.BASEEXP,(1, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        catch_rate_base_exp.SetSizerAndFit(catch_rate_base_exp_sizer)
        self.sizer.Add(catch_rate_base_exp, (2,0), wx.DefaultSpan,  wx.ALL, 2)
        
        #----------Set up a panel for EVs----------#
        evs = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        evs_sizer = wx.GridBagSizer(3,3)
        
        e_txt = wx.StaticText(evs, -1,"Effort Values:")
        evs_sizer.Add(e_txt, (0, 0), (1,2), wx.EXPAND)
        
        e_HP_txt = wx.StaticText(evs, -1,"HP:")
        evs_sizer.Add(e_HP_txt, (1, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.e_HP = wx.TextCtrl(evs, -1,style=wx.TE_CENTRE, size=(40,-1))
        evs_sizer.Add(self.e_HP,(1, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        e_ATK_txt = wx.StaticText(evs, -1,"ATK:")
        evs_sizer.Add(e_ATK_txt, (2, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.e_ATK = wx.TextCtrl(evs, -1,style=wx.TE_CENTRE, size=(40,-1))
        evs_sizer.Add(self.e_ATK,(2, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        e_DEF_txt = wx.StaticText(evs, -1,"DEF:")
        evs_sizer.Add(e_DEF_txt, (3, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.e_DEF = wx.TextCtrl(evs, -1,style=wx.TE_CENTRE, size=(40,-1))
        evs_sizer.Add(self.e_DEF,(3, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        e_SPD_txt = wx.StaticText(evs, -1,"SPD:")
        evs_sizer.Add(e_SPD_txt, (4, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.e_SPD = wx.TextCtrl(evs, -1,style=wx.TE_CENTRE, size=(40,-1))
        evs_sizer.Add(self.e_SPD,(4, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        e_SpATK_txt = wx.StaticText(evs, -1,"Sp. ATK:")
        evs_sizer.Add(e_SpATK_txt, (5, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.e_SpATK = wx.TextCtrl(evs, -1,style=wx.TE_CENTRE, size=(40,-1))
        evs_sizer.Add(self.e_SpATK,(5, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        e_SpDEF_txt = wx.StaticText(evs, -1,"Sp. DEF:")
        evs_sizer.Add(e_SpDEF_txt, (6, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.e_SpDEF = wx.TextCtrl(evs, -1,style=wx.TE_CENTRE, size=(40,-1))
        evs_sizer.Add(self.e_SpDEF,(6, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        evs.SetSizerAndFit(evs_sizer)
        self.sizer.Add(evs, (0,1), wx.DefaultSpan,  wx.ALL, 2)
        
        #----------Panel for items----------#
        items = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        items_sizer = wx.GridBagSizer(3,3)
        
        items_offset = int(frame.Config.get(frame.rom_id, "Items"), 16)
        number_of_items = int(frame.Config.get(frame.rom_id, "NumberofItems"), 16)
        item_data_len = int(frame.Config.get(frame.rom_id, "ItemsDataLength"), 16)
        
        items_list = generate_list_of_names(items_offset, item_data_len, 
                            "\xff", number_of_items, frame.open_rom)
                            
        ITEM1_txt = wx.StaticText(items, -1,"Item 1:")
        items_sizer.Add(ITEM1_txt, (0, 0), wx.DefaultSpan,  wx.ALL, 4)
        self.ITEM1 = wx.ComboBox(items, -1, choices=items_list,
                                style=wx.SUNKEN_BORDER, size=(110, 20))
        items_sizer.Add(self.ITEM1, (0, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        ITEM2_txt = wx.StaticText(items, -1,"Item 2:")
        items_sizer.Add(ITEM2_txt, (1, 0), wx.DefaultSpan,  wx.ALL, 4)
        self.ITEM2 = wx.ComboBox(items, -1, choices=items_list,
                                style=wx.SUNKEN_BORDER, size=(110, 20))
        items_sizer.Add(self.ITEM2, (1, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        items.SetSizerAndFit(items_sizer)
        self.sizer.Add(items, (1,1), wx.DefaultSpan,  wx.ALL, 2)
        
        #----------Panel for Gender, Hatch Speed, Friendship, Level-up speed, and egg groups----------#
        assorted = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        assorted_sizer = wx.GridBagSizer(3,3)
        
        GENDER_txt = wx.StaticText(assorted, -1,"Gender Ratio:")
        assorted_sizer.Add(GENDER_txt, (0, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.GENDER = wx.TextCtrl(assorted, -1,style=wx.TE_CENTRE, size=(40,-1))
        assorted_sizer.Add(self.GENDER, (0, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        HATCH_txt = wx.StaticText(assorted, -1,"Hatch Speed:")
        assorted_sizer.Add(HATCH_txt, (1, 0), wx.DefaultSpan,  wx.ALL, 6)
        self.HATCH = wx.TextCtrl(assorted, -1,style=wx.TE_CENTRE, size=(40,-1))
        assorted_sizer.Add(self.HATCH, (1, 1), wx.DefaultSpan,  wx.ALL, 4)
        
        assorted.SetSizerAndFit(assorted_sizer)
        self.sizer.Add(assorted, (0,2), wx.DefaultSpan,  wx.ALL, 2)
        #---------- ----------#
        self.load_stats_into_boxes()
        self.create_string_of_hex_values_to_be_written()
        
    def load_stats_into_boxes(self):
        d = self.base_stats_dict
        self.HP.SetValue(str(d["HP"]))
        self.ATK.SetValue(str(d["ATK"]))
        self.DEF.SetValue(str(d["DEF"]))
        self.SPD.SetValue(str(d["SPD"]))
        self.SpATK.SetValue(str(d["SAT"]))
        self.SpDEF.SetValue(str(d["SDE"]))
        
        self.TYPE1.SetSelection(d["TYPE1"])
        self.TYPE2.SetSelection(d["TYPE2"])
        
        self.CATCHRATE.SetValue(str(d["CATCHRATE"]))
        self.BASEEXP.SetValue(str(d["BASEEXP"]))
        
        self.e_HP.SetValue(str(d["EVS"][3]))
        self.e_ATK.SetValue(str(d["EVS"][2]))
        self.e_DEF.SetValue(str(d["EVS"][1]))
        self.e_SPD.SetValue(str(d["EVS"][0]))
        self.e_SpATK.SetValue(str(d["EVS"][6]))
        self.e_SpDEF.SetValue(str(d["EVS"][7]))
        
        self.ITEM1.SetSelection(d["ITEM1"])
        self.ITEM2.SetSelection(d["ITEM2"])
        
        self.GENDER.SetValue(str(d["GENDER"]))
        self.HATCH.SetValue(str(d["HATCHINGSTEPS"]))
        
    def create_string_of_hex_values_to_be_written(self):
        try:
            HP = hex(int(self.HP.GetValue()))[2:]
            if len(HP) > 2:
                HP = "FF"
            elif len(HP) == 0:
                HP = "00"
            elif len(HP) == 1:
                HP = "0"+HP
                
            ATK = hex(int(self.ATK.GetValue()))[2:]
            if len(ATK) > 2:
                ATK = "FF"
            elif len(ATK) == 0:
                ATK = "00"
            elif len(ATK) == 1:
                ATK = "0"+ATK
                
            DEF = hex(int(self.DEF.GetValue()))[2:]
            if len(DEF) > 2:
                DEF = "FF"
            elif len(DEF) == 0:
                DEF = "00"
            elif len(DEF) == 1:
                DEF = "0"+DEF
                 
            SPD = hex(int(self.SPD.GetValue()))[2:]
            if len(SPD) > 2:
                SPD = "FF"
            elif len(SPD) == 0:
                SPD = "00"
            elif len(SPD) == 1:
                SPD = "0"+SPD
                 
            SpATK = hex(int(self.SpATK.GetValue()))[2:]
            if len(SpATK) > 2:
                SpATK = "FF"
            elif len(SpATK) == 0:
                SpATK = "00"
            elif len(SpATK) == 1:
                SpATK = "0"+SpATK
                 
            SpDEF = hex(int(self.SpDEF.GetValue()))[2:]
            if len(SpDEF) > 2:
                SpDEF = "FF"
            elif len(SpDEF) == 0:
                SpDEF = "00"
            elif len(SpDEF) == 1:
                SpDEF = "0"+SpDEF
                 
            TYPE1 = hex(int(self.TYPE1.GetSelection()))[2:]
            if len(TYPE1) == 1:
                TYPE1 = "0"+TYPE1
                 
            TYPE2 = hex(int(self.TYPE2.GetSelection()))[2:]
            if len(TYPE2) == 1:
                TYPE2 = "0"+TYPE2
            
            CATCHRATE = hex(int(self.CATCHRATE.GetValue()))[2:]
            if len(CATCHRATE) > 2:
                CATCHRATE = "FF"
            elif len(CATCHRATE) == 0:
                CATCHRATE = "00"
            elif len(CATCHRATE) == 1:
                CATCHRATE = "0"+CATCHRATE
                
            BASEEXP = hex(int(self.BASEEXP.GetValue()))[2:]
            if len(BASEEXP) > 2:
                BASEEXP = "FF"
            elif len(BASEEXP) == 0:
                BASEEXP = "00"
            elif len(BASEEXP) == 1:
                BASEEXP = "0"+BASEEXP
                
            evs_list = [str(self.e_SPD.GetValue()), str(self.e_DEF.GetValue()),
                            str(self.e_ATK.GetValue()), str(self.e_HP.GetValue()),
                            "0","0",str(self.e_SpATK.GetValue()),
                            str(self.e_SpDEF.GetValue())]
            evs_bin = ""
            for i, value in enumerate(evs_list):
                if i == 4:
                    evs_bin = evs_bin+"00"
                elif i == 5:
                    evs_bin = evs_bin+"00"
                else:
                    if len(value) > 1:
                        value = "3"
                    elif value == "":
                        value = "0"
                    ev = bin(int(value))[2:].zfill(2)
                    evs_bin = evs_bin+ev
            evs_hex = hex(int(evs_bin, 2))[2:]

            ITEM1 = hex(int(self.ITEM1.GetSelection()))[2:]
            ITEM1_len = len(ITEM1)
            if ITEM1_len < 4:
                for n in range(4-ITEM1_len):
                    ITEM1 = "0"+ITEM1
            ITEM1 = ITEM1[2:]+ITEM1[:2] #Flip the bytes around.

            ITEM2 = hex(int(self.ITEM2.GetSelection()))[2:]
            ITEM2_len = len(ITEM2)
            if ITEM2_len < 4:
                for n in range(4-ITEM2_len):
                    ITEM2 = "0"+ITEM2
            ITEM2 = ITEM2[2:]+ITEM2[:2] #Flip the bytes around.
            
            GENDER = hex(int(self.GENDER.GetValue()))[2:]
            if len(GENDER) > 2:
                GENDER = "FF"
            elif len(GENDER) == 0:
                GENDER = "00"
            elif len(GENDER) == 1:
                GENDER = "0"+GENDER
                
            HATCH = hex(int(self.HATCH.GetValue()))[2:]
            if len(HATCH) > 2:
                HATCH = "FF"
            elif len(HATCH) == 0:
                HATCH = "00"
            elif len(HATCH) == 1:
                HATCH = "0"+HATCH
                
            #Create a string off all of the stats to be written to the rom.
            base = HP+ATK+DEF+SPD+SpATK+SpDEF
            types = TYPE1+TYPE2
            rate_exp = CATCHRATE+BASEEXP
            evs = evs_hex
            items = ITEM1+ITEM2
            assort = GENDER+HATCH
            
            stats = base+types+rate_exp+evs+items+assort
            print stats
            
            
            
        except:
            pass
            #need to print an error here.
        
    def sort_base_stats(self):
        d = self.base_stats_dict
        s = self.basestats
        d["HP"] = int(get_bytes_string_from_hex_string(s[0]),16)
        d["ATK"] = int(get_bytes_string_from_hex_string(s[1]),16)
        d["DEF"] = int(get_bytes_string_from_hex_string(s[2]),16)
        d["SPD"] = int(get_bytes_string_from_hex_string(s[3]),16)
        d["SAT"] = int(get_bytes_string_from_hex_string(s[4]),16)
        d["SDE"] = int(get_bytes_string_from_hex_string(s[5]),16)
        d["TYPE1"] = int(get_bytes_string_from_hex_string(s[6]),16)
        d["TYPE2"] = int(get_bytes_string_from_hex_string(s[7]),16)
        d["CATCHRATE"] = int(get_bytes_string_from_hex_string(s[8]),16)
        d["BASEEXP"] = int(get_bytes_string_from_hex_string(s[9]),16)
        #Deal with EV bits:
        evs = get_bytes_string_from_hex_string(s[10]+s[11])
        scale = 16 ## equals to hexadecimal
        num_of_bits = 16
        evs = bin(int(evs, scale))[2:].zfill(num_of_bits)
        evs_list = split_string_into_bytes(evs)
        evs_list_ints = []
        for ev in evs_list:
            ev = int(ev,2)
            evs_list_ints.append(ev)
        d["EVS"] = evs_list_ints
        #Done with evs....
        d["ITEM1"] = int(get_bytes_string_from_hex_string(s[13]+s[12]),16)
        d["ITEM2"] = int(get_bytes_string_from_hex_string(s[15]+s[14]),16)
        d["GENDER"] = int(get_bytes_string_from_hex_string(s[16]),16)
        d["HATCHINGSTEPS"] = int(get_bytes_string_from_hex_string(s[17]),16)
        d["FRIENDSHIP"] = int(get_bytes_string_from_hex_string(s[18]),16)
        d["LEVELUPTYPE"] = int(get_bytes_string_from_hex_string(s[19]),16)
        d["EGGGROUP1"] = int(get_bytes_string_from_hex_string(s[20]),16)
        d["EGGGROUP2"] = int(get_bytes_string_from_hex_string(s[21]),16)
        d["ABILITY1"] = int(get_bytes_string_from_hex_string(s[22]),16)
        d["ABILITY2"] = int(get_bytes_string_from_hex_string(s[23]),16)
        d["RUNRATE"] = int(get_bytes_string_from_hex_string(s[24]),16)
        d["COLOR"] = int(get_bytes_string_from_hex_string(s[25]),16)
        
        self.base_stats_dict = d
        
class MovesTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(sizer)

class EvoTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(sizer)

class PokeDexTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(sizer)
#############################################################



app = wx.App(False)
frame = MainWindow(None, "Pokemon Gen III Hacking Suite")
app.MainLoop()
