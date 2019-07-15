# Parses Project Scripts, Base Scripts, Definition Files, and CRC Files

# TODO: figure out what is $CRCCHECK is
# may need to add a /crccheck launch option to have this thing only check the crc of a file

import os
import hashlib
import PyQPC_Base as base


class ProjectBlock:
    def __init__(self, key, values=[], conditional=None):
        self.key = key
        self.values = []
        self.values.extend(values)
        self.conditional = conditional
        self.items = []

    def AddItem(self, item):
        self.items.append(item)


class Project:
    def __init__(self, name, path, macros, conditionals):
        self.file_name = name  # the actual file name
        self.name = name  # the project name
        # self.path = path # folder the project script is in (using $PROJECTDIR instead, maybe use this instead?)

        # i might change this to just be a huge list, and have the folder it goes in in the file object
        self.files = []  # dictionary because folders

        self.libraries = []  # maybe change to dependencies?

        # maybe add an "self.other_files" dictionary where the files aren't objects and just the paths?
        # and only use self.files for h and cpp files?

        # if the key is an integer, it's a file
        # if the key is a string, it's a folder

        self.config = {}

        # self.project_scripts = []

        self.crc_list = {}

        self.macros = {"$PROJECTDIR": path, "$PROJECTNAME": name}
        for key, value in macros.items():
            self.macros[key] = value

        self.macros_required = {}

        self.conditionals = {}
        for key, value in conditionals.items():
            self.conditionals[key] = value

    def AddMacro(self, values, required=False):
        key_name = "$" + values[0].upper()

        try:
            value = values[1]
        except:
            value = ''

        if required and value == '':
            if key_name not in self.macros:
                self.macros_required[key_name] = value
        else:
            # remove it from the required list if it's in it?
            if key_name in self.macros_required:
                del self.macros_required[key_name]
            if key_name not in self.macros:
                self.macros[key_name] = value

        self.ReplaceAnyUndefinedMacros()
        self.AddConditional(values)

        return

    def ReplaceAnyUndefinedMacros(self):
        # this could probably be sped up 
        # TODO: add scanning of files and certain config settings
        for macro, value in self.macros.items():
            self.macros[macro] = ReplaceMacros(value, self.macros, self.macros_required)

    def AddConditional(self, values):

        if len(values) < 2:
            return

        try:
            self.conditionals["$" + values[0].upper()] = int(values[1])
        except ValueError:
            pass

    def AddFile(self, folder_list, file_list):

        for file_path in file_list:

            # TODO: add a cmd option check for /hidewarnings here
            if self.GetFileObject(file_path):
                if not base.FindCommand("/hidewarnings"):
                    print("WARNING: File already added: \"" + file_path + "\"")
                return

            self.files.append(ProjectFile(file_path, folder_list, self.config))

    def GetAllFileFolderDepthLists(self):

        folder_lists = []
        for file_obj in self.files:
            if file_obj.folder_depth_list not in folder_lists and file_obj.folder_depth_list != []:
                folder_lists.append(file_obj.folder_depth_list)

        return folder_lists

    def GetAllFileFolderPaths(self):

        folder_paths = []
        for file_obj in self.files:
            if file_obj.folder_path not in folder_paths and file_obj.folder_path != '':
                folder_paths.append(file_obj.folder_path)

        return folder_paths

    def GetFileObjectsInFolder(self, folder_list):

        file_obj_list = []
        for file_obj in self.files:
            if file_obj.folder_depth_list == folder_list:
                file_obj_list.append(file_obj)

        return file_obj_list

    def GetFileObject(self, file_path):

        for file_obj in self.files:
            if file_obj.path == file_path:
                return file_obj

        return False

    # TODO: i probably need to add more stuff here for the prefix and ext macros
    # also add a check file option, since sometimes i may use "$DynamicFile" for a lib
    # maybe make a DynamicLib option? idk
    def AddLib(self, lib_path, implib=False):
        # TODO: fix this for if you have multiple libs in the value
        lib_path = lib_path[0]

        # remove this ugly ass hack valve did later
        if not os.sep in lib_path:
            lib_path = self.macros["$LIBPUBLIC"] + os.sep + lib_path

        # wow u dumb
        '''
        try:
            # get rid of the path separators if there are any
            file_name = file
            if os.sep in file_name:
                file_name = file.rsplit( os.sep, 1 )[1]

            # try splitting it to get the file extension, it will throw an exception if doesn't have one
            file_ext_test = file_name.rsplit( ".", 1 )[1]

        except:
        '''

        if implib:
            lib_ext = self.macros["$_STATICLIB_EXT"]
        else:
            lib_ext = self.macros["$_STATICLIB_EXT"]

        if not lib_path.endswith(lib_ext):
            lib_path += lib_ext

        if lib_path not in self.libraries:
            self.libraries.append(lib_path)
        else:
            if not base.FindCommand("/hidewarnings"):
                print("WARNING: Library already added: \"" + lib_path + "\"")

    def RemoveLib(self, file, implib=False):
        # TODO: fix this for if you have multiple libs in the value
        file = file[0]

        # remove this ugly ass hack valve did later
        if not os.sep in file:
            file = self.macros["$LIBPUBLIC"] + os.sep + file

        if implib:
            file += self.macros["$_IMPLIB_EXT"]
        else:
            file += self.macros["$_STATICLIB_EXT"]

        del self.libraries[self.libraries.index(file)]

    def RemoveFile(self, file_list):

        for file_obj in self.files:
            if file_obj.path in file_list:
                del self.files[self.files.index(file_obj)]
                break


class ProjectFile:
    def __init__(self, file_path, folder_list, project_config):
        self.path = file_path
        self.config = {}

        # maybe add a file extension value?

        # folder layout in any editor you want to use
        self.folder_depth_list = []
        self.folder_depth_list.extend(folder_list)  # make sure it's a list even if it's a string
        self.folder_path = os.sep.join(folder_list)

        for config_name in project_config:
            base.CreateNewDictValue(self.config, config_name, "dict")


def AddConfig(project, config):
    if config != '':
        base.CreateNewDictValue(project.config, config, "dict")


def AddConfigGroup(project, config, group_name):
    if config == '':
        for config_name in project.config:
            base.CreateNewDictValue(project.config[config_name], group_name, "dict")
    else:
        base.CreateNewDictValue(project.config[config], group_name, "dict")


def _AddConfigOption(project, config, group_name, option_name, option_value, option_definition):
    if type(option_value) == str:  # and self.config[ config ][ group_name ][ option_name ] != '':
        base.CreateNewDictValue(project.config[config][group_name], option_name, "str")

        if "$BASE" in option_value:
            # add onto what we already have

            base_value = project.config[config][group_name][option_name]

            '''
            option_value_split = option_value.split("$BASE")

            if option_definition.prefer_semicolon_no_comma or option_definition.prefer_semicolon_no_space:
                if not base_value.endswith( ";" ):
                    if not option_value_split[0].endswith( ";" ):
                        if not option_value_split[1].startswith( ";" ):
                            base_value += ";"
            '''

            option_value = option_value.replace("$BASE", base_value)

        project.config[config][group_name][option_name] = option_value
    else:
        project.config[config][group_name].update({option_name: option_value})


def _AddFileConfigOption(project, file_obj, config, group_name, option_name, option_value, option_definition):
    if type(option_value) == str:  # and self.config[ config ][ group_name ][ option_name ] != '':
        base.CreateNewDictValue(file_obj.config[config][group_name], option_name, "str")

        if "$BASE" in option_value:
            # add everything from the project and what we may already have

            # try:
            #     base_value = project.config[config][group_name][option_name]
            # except KeyError:
            #     base_value = ''

            base_value = project.config[config][group_name][option_name]
            option_value = ''.join(option_value.split("$BASE"))

            if option_definition.prefer_semicolon_no_comma or option_definition.prefer_semicolon_no_space:
                if not base_value.endswith(";"):
                    if not option_value.startswith(";"):
                        base_value += ";"

            file_obj.config[config][group_name][option_name] = base_value + option_value

            # file_obj.config[config][group_name][option_name] += value + ''.join( option_value.split("$BASE") )
        else:
            file_obj.config[config][group_name][option_name] = option_value
    else:
        file_obj.config[config][group_name].update({option_name: option_value})


def AddConfigOption(project, config, group_name, option_name, option_value, option_definition, file_obj=None):
    # check if the config name is '', if it is, add it to all configurations
    # this won't add onto an option, this will just replace it
    # so maybe check the type for if we should replace it or not
    if config == '':
        for config_name in project.config:
            if file_obj:
                _AddFileConfigOption(project, file_obj, config_name, group_name, option_name, option_value,
                                     option_definition)
            else:
                _AddConfigOption(project, config_name, group_name, option_name, option_value, option_definition)
    else:
        if file_obj:
            _AddFileConfigOption(project, file_obj, config, group_name, option_name, option_value, option_definition)
        else:
            _AddConfigOption(project, config, group_name, option_name, option_value, option_definition)
    return


def GetConfigOptionValue(project, config, group_name, option_name, option_value, file_obj=None):
    if not option_value or config == '':
        return

    if file_obj:
        try:
            return file_obj.config[config][group_name][option_name]
        except KeyError:
            return None

    else:
        try:
            return project.config[config][group_name][option_name]
        except KeyError:
            return None


class DefinitionsFile:
    def __init__(self, file):
        self.file = file
        self.version = 0
        self.groups = {}

    def SetVersion(self, version):
        self.version = int(version)

    def AddGroup(self, group_name):
        base.CreateNewDictValue(self.groups, group_name, "list")

    def AddOption(self, group_name, option):
        self.groups[group_name].append(option)


class ConfigOption:
    def __init__(self, key):
        self.key = key
        self.type = "ignore"

        # this is a list because the order of these matter, as it uses the top one by default
        self.ordinals = []

        self.output = None  # what the key name will be instead

        # alternative key names
        self.alias = None
        self.legacy = None

        # booleans
        self.append_slash = False  # adds a slash to the end of it?
        self.fix_slashes = False
        self.prefer_semicolon_no_comma = False
        self.prefer_semicolon_no_space = False
        self.invert_output = False

        # idk yet
        self.global_property = False  # allows this key to be used anywhere

    def AddOrdinalOption(self, key, value):
        self.ordinals.append(dict({key: value}))
        # self.ordinals[ key ] = value

    def ConvertOrdinal(self, value):
        if not value:
            return None

        # TODO: change self.ordinals to a dictionary, having it as a list is dumb
        for ordinal in self.ordinals:
            if value[0] in ordinal:
                return ordinal[value[0]]
        else:
            print("ERROR: Unknown Ordinal option: " + value)
            quit()


# maybe add a depth variable here as well? idk
def ReadFile(path, **kwargs):
    with open(path, mode="r", encoding="utf-8") as file:
        file = file.readlines()
    file = base.RemoveCommentsAndFixLines(file)
    file = CleanFile(file)

    return file


# Purpose: to clean up the project script to make parsing it easier
def CleanFile(file):
    cleaned_file = []

    line_num = 0
    while line_num < len(file):

        if file[line_num] == '':
            line_num += 1
            continue

        block = GetFileBlockSplit(file, line_num, False)

        line_num = block[0] - 1
        block = CreateFileBlockObject(block[1])
        cleaned_file.append(block)

        line_num += 1
        continue

    return cleaned_file


def CreateFileBlockObject(block):
    value_list = []
    conditional = None

    value_index = 1
    while len(block[0]) > value_index:

        # don't add any conditional to the value_list
        if "[" in block[0][value_index] or "]" in block[0][value_index]:
            conditional = block[0][value_index][1:-1]  # no brackets on the ends
        else:
            value_list.append(base.RemoveQuotes(block[0][value_index]))
        value_index += 1

    key = ProjectBlock(block[0][0], value_list, conditional)

    if len(block) > 1:

        block_line_num = 1
        while block_line_num < len(block):

            if block[block_line_num] != [] and block[block_line_num][0] != '{' and block[block_line_num][0] != '}':

                sub_block = GetFileBlockSplit(block, block_line_num)

                if isinstance(sub_block[1], list):
                    block_line_num = sub_block[0]  # - 1
                    sub_block = CreateFileBlockObject(sub_block[1])
                    key.AddItem(sub_block)
                    continue

            block_line_num += 1

    return key


# Returns a block into a list with each string split up starting from a line number
def GetFileBlockSplit(file, line_number, has_split_lines=True):
    if has_split_lines:
        line_split = file[line_number]
    else:
        line_split = base.CleanUpSplitLine(file[line_number].split(" "))

    block_depth_num = 0

    block = [line_split]
    if line_split == ['{']:
        block_depth_num = 1

    line_number += 1

    if has_split_lines:
        if file[line_number] != ["{"]:
            return [line_number, block]

    while line_number < len(file):

        if has_split_lines:
            line_split = file[line_number]
        else:
            line_split = base.CleanUpSplitLine(file[line_number].split(" "))

        # the value is split across multiple lines
        if len(block[-1]) > 1 and block[-1][-1] == "\\":
            if line_split != []:
                del block[-1][-1]
                block[-1].extend(line_split)
            line_number += 1
            continue
        else:
            if block_depth_num == 0 and line_split == []:
                break

        if line_split != []:
            if (line_split == ['{']) or (block_depth_num != 0):
                block.append(line_split)

            elif len(block[-1]) > 1:
                if block_depth_num == 0:
                    # this is a single line block like $Macro
                    break

            # this has never called yet, odd
            elif file[line_number] != '' and "{" in file[line_number]:
                # there are items in this block, so add them
                sub_block = GetFileBlockSplit(file, line_number + 1, has_split_lines)
                line_number = sub_block[0]
                block.extend(sub_block[1])
            else:
                break

        if "{" in line_split:
            block_depth_num += 1

        if "}" in line_split:
            block_depth_num -= 1

        line_number += 1

    return [line_number, block]


def ParseBaseFile(base_file, macros, conditionals, unknown_conditionals, project_list, group_list):
    # print( "Parsing Base File: " + "name" )

    definitions_file_path = None

    for project_block in base_file:

        key = project_block.key.casefold()  # compare with ignoring case

        if key == "$CommandLineConditionals".casefold():

            for sub_project_block in project_block.items:
                if sub_project_block.key.upper() in unknown_conditionals:
                    if base.SolveConditional(sub_project_block.conditional, conditionals):
                        conditionals["$" + sub_project_block.key.upper()] = 1
                        del unknown_conditionals[unknown_conditionals.index(sub_project_block.key.upper())]

        elif key == "$Project".casefold():
            base.CreateNewDictValue(project_list, project_block.values[0].casefold(), "list")

            for item in project_block.items:
                if base.SolveConditional(item.conditional, conditionals):
                    item.key = ReplaceMacros(item.key, macros)
                    project_list[project_block.values[0].casefold()].append(item.key)

        elif key == "$Group".casefold():
            # TODO: fix this for multiple groups
            base.CreateNewDictValue(group_list, project_block.values[0], "list")

            for item in project_block.items:
                if base.SolveConditional(item.conditional, conditionals):
                    item.key = ReplaceMacros(item.key, macros)
                    group_list[project_block.values[0].casefold()].append(item.key)

        elif key == "$Definitions".casefold():
            definitions_file_path = ReplaceMacros(project_block.values[0], macros)

        elif project_block.key.casefold() == "$Conditional".casefold():
            # TODO_ERROR: add error checking here if value_str can't be an integer and if no value was given
            conditionals["$" + project_block.values[0].upper()] = int(project_block.values[1])

        elif project_block.key.casefold() == "$Macro".casefold():
            macros["$" + project_block.values[0].upper()] = ReplaceMacros(project_block.values[1], macros)

        # FIX THIS
        elif project_block.key.casefold() == "$MacroRequired".casefold():
            macros["$" + project_block.values[0].upper()] = ReplaceMacros(project_block.values[1], macros)

        elif project_block.key.casefold() == "$Include".casefold():
            # "Ah shit, here we go again."
            path = os.path.normpath(ReplaceMacros(project_block.values[0], macros))

            # maybe add a depth counter like in parsing projects?
            if base.FindCommand("/verbose"):
                print("Reading: " + path)

            include_file = ReadFile(path)
            ParseBaseFile(include_file, macros, conditionals, unknown_conditionals, project_list, group_list)

        else:
            print("Unknown Key: " + project_block.key)

    return definitions_file_path


def ParseProjectFile(project_file, project, definitions, depth=0):
    for project_block in project_file:

        key = project_block.key.casefold()  # compare with ignoring case

        # check if the conditional result is true before checking the key
        if base.SolveConditional(project_block.conditional, project.conditionals):

            # replace any macros HERE, not in each function
            # this better not cause any issues...
            for value in project_block.values:
                index = project_block.values.index(value)
                project_block.values[index] = ReplaceMacros(value, project.macros, project.macros_required)

            if key == "$configuration":
                ParseConfigBlock(project_block, project, definitions, project.conditionals, project.macros,
                                 project.macros_required)

            elif key == "$project":
                ParseProjectBlock(project_block, project, definitions)

            elif key == "$conditional":
                project.AddConditional(project_block.values)

            elif key == "$macro":
                project.AddMacro(project_block.values)

            elif key == "$macrorequired":
                project.AddMacro(project_block.values, True)

            elif key == "$macrorequiredallowempty":
                project.AddMacro(project_block.values, True)

            elif key == "$include":
                # Ah shit, here we go again.
                # path = ReplaceMacros( project_block.values[0], project.macros, project.macros_required )
                path = project_block.values[0]

                if base.FindCommand("/verbose"):
                    depth += 1
                    space = []
                    while len(space) < depth:
                        space.append("    ")

                    print(''.join(space) + "Reading: " + path)

                # full_path = os.path.join( project.macros[ "$PROJECTDIR" ], path )
                full_path = os.path.normpath(project.macros["$PROJECTDIR"] + os.sep + path)

                project.crc_list[path] = MakeCRC(full_path)

                include_file = ReadFile(full_path)

                if base.FindCommand("/verbose"):
                    print(''.join(space) + "Parsing: " + path)

                ParseProjectFile(include_file, project, definitions, depth)

                if base.FindCommand("/verbose"):
                    print(''.join(space) + "Parsed: " + path)
                    depth -= 1

            elif key == "$IgnoreRedundancyWarning".casefold() or key == "$linux" or key == "$LoadAddressMacro".casefold() or key == "$LoadAddressMacroAuto".casefold():
                pass

            else:
                print("ERROR: Unknown key found: " + key)

    return  # project


def ParseProjectBlock(project_block, project, definitions):
    # project.AddFileFolder( folder_list )
    # project.AddFile( folder_list, file )
    # project.GetFileObject( file )
    # project.AddLib( file, implib = False )
    # project.RemoveLib( file, implib = False )
    # project.RemoveFile( file )

    if base.SolveConditional(project_block.conditional, project.conditionals):

        # if project_block.values != []:
        if project_block.values:
            project.name = project_block.values[0]

        # now go through each item
        for block in project_block.items:
            if base.SolveConditional(block.conditional, project.conditionals):

                for value in block.values:
                    index = block.values.index(value)
                    block.values[index] = ReplaceMacros(value, project.macros, project.macros_required)

                if block.key.casefold() == "$folder":
                    ParseFolder(block, project, definitions)

                elif "$file" in block.key.casefold() or "$dynamicfile" in block.key.casefold() \
                    or "$lib" in block.key.casefold() or "$implib" in block.key.casefold():
                    ParseFile(block, project, definitions)

                else:
                    print("Unknown Key: " + block.key)


def ParseFolder(folder_block, project, definitions, folder_list=[]):
    # project.AddFileFolder( folder_list )
    # project.AddFile( folder_list, file )
    # project.GetFileObject( file )
    # project.AddLib( file, implib = False )
    # project.RemoveLib( file, implib = False )
    # project.RemoveFile( file )

    folder_list.append(folder_block.values[0])
    # project.AddFileFolder( folder_list )

    for block in folder_block.items:
        if base.SolveConditional(block.conditional, project.conditionals):

            for value in block.values:
                index = block.values.index(value)
                block.values[index] = ReplaceMacros(value, project.macros, project.macros_required)

            if block.key.casefold() == "$folder":
                ParseFolder(block, project, definitions, folder_list)

            elif "$file" in block.key.casefold() or "$dynamicfile" in block.key.casefold() \
                or "$lib" in block.key.casefold() or "$implib" in block.key.casefold():
                ParseFile(block, project, definitions, folder_list)

            elif "$shaders" in block.key.casefold():
                pass

            else:
                print("Unknown Key: " + block.key)

    # now "leave" the last folder
    del folder_list[-1]


def ParseFile(file_block, project, definitions, folder_list=[]):
    # project.AddFile( folder_list, file )
    # project.GetFileObject( file )
    # project.AddLib( file, implib = False )
    # project.RemoveLib( file, implib = False )
    # project.RemoveFile( file )

    # for value in file_block.values:
    # index = file_block.values.index( value )
    # file_block.values[ index ] = ReplaceMacros( value, project.macros, project.macros_required )

    # ew
    if folder_list != [] and folder_list[-1] == "Link Libraries":
        if not "lib" in file_block.key.casefold():
            file_block.key = "$Lib"

    if file_block.key.casefold() == "$file":
        project.AddFile(folder_list, file_block.values)

        if file_block.items != []:
            for file_path in file_block.values:
                file_object = project.GetFileObject(file_path)
                ParseConfigBlock(file_block.items[0], project, definitions, project.conditionals, project.macros,
                                 project.macros_required, file_object)

    elif file_block.key.casefold() == "$dynamicfile":
        project.AddFile(folder_list, file_block.values)
        # these don't have config blocks, right? idk
        # not hard to add though, just copy the 3 lines above

    elif file_block.key.casefold() == "$lib":
        project.AddLib(file_block.values)

    elif file_block.key.casefold() == "$implib":
        project.AddLib(file_block.values, True)

    # ----------------------------------------------------------
    # Removing Files now
    elif file_block.key.casefold() == "-$file":
        project.RemoveFile(file_block.values)

    elif file_block.key.casefold() == "-$lib":
        project.RemoveLib(file_block.values)

    elif file_block.key.casefold() == "-$implib":
        project.RemoveLib(file_block.values, True)

    else:
        print("unknown key: " + file_block.key)


# dammit, i accidentally made this so you can only have an option in a group
# and can't have a group in a group, not really sure if i should bother fixing it right now though
# TODO: split this up into ParseConfigGroup() and ParseConfigOption(), so you can parse it recursively
def ParseConfigBlock(project_block, project, definitions, conditionals, macros, macros_required, file_obj=None):
    # TODO: do something with the definitions here, maybe check what it is? idfk
    # or maybe add that definition option into the project config?

    if project_block.values == []:
        config_name = ""  # add it to all configs
        # platform = "" # all platforms as well
    else:
        config_name = project_block.values[0]
        # if len(values) > 1:
        #   platform = project_block.values[1]
        # else:
        #   platform = ""  # add the options to all platforms in this config

    if base.SolveConditional(project_block.conditional, conditionals):

        if file_obj:
            AddConfig(file_obj, config_name)
        else:
            AddConfig(project, config_name)

        for group_block in project_block.items:
            if base.SolveConditional(group_block.conditional, conditionals):
                if group_block.key in definitions.groups:

                    if file_obj:
                        AddConfigGroup(file_obj, config_name, group_block.key)
                    else:
                        AddConfigGroup(project, config_name, group_block.key)

                    for option_block in group_block.items:
                        if base.SolveConditional(option_block.conditional, conditionals):

                            # maybe move this to ParseConfigOption()?
                            # that way you don't have to use an option in a group? idk
                            compare_name = option_block.key.casefold()
                            for option_definition in definitions.groups[group_block.key]:
                                # PAIN
                                if compare_name == option_definition.key.casefold() or \
                                    (option_definition.alias and compare_name == option_definition.alias.casefold()) or \
                                    (option_definition.legacy and compare_name == option_definition.legacy.casefold()):

                                    # floods the console with $PrecompiledHeaderFile
                                    if base.FindCommand("/showlegacyoptions"):
                                        if option_definition.legacy != None and compare_name == option_definition.legacy.casefold():
                                            print("Legacy option: " + option_block.key)

                                    if option_definition.output:
                                        name = option_definition.output
                                    else:
                                        name = option_definition.key
                                    value = option_block.values

                                    if value == []:
                                        break

                                    if "$" in name:
                                        name = name.split("$", 1)[1]

                                    if option_definition.type == "ignore":
                                        break
                                    elif option_definition.type == "string":
                                        value = ReplaceMacros(''.join(option_block.values), macros, macros_required)

                                    elif option_definition.type == "ordinals":
                                        value = option_definition.ConvertOrdinal(value)

                                    elif option_definition.type == "bool":
                                        if value[0].lower().startswith("no") or value[0].lower().startswith("false"):
                                            value = "False"
                                        elif value[0].lower().startswith("yes") or value[0].lower().startswith("true"):
                                            value = "True"
                                        else:
                                            print("unknown bool option: " + value)

                                        if option_definition.invert_output:
                                            value = not value

                                    elif option_definition.type == "integer":
                                        print("integer is not setup yet as it is never used")

                                    else:
                                        print("unknown key type: " + option_definition.key)

                                    # should i use the replace function instead?
                                    if option_definition.prefer_semicolon_no_comma:
                                        value = value.replace(",", ";")

                                    if option_definition.prefer_semicolon_no_space:
                                        value = value.replace(" ", ";")

                                    if option_definition.append_slash:
                                        if not value.endswith(os.sep):
                                            value = value + os.sep

                                    if option_definition.fix_slashes:
                                        if value != '':
                                            value = os.path.normpath(value)

                                    if value:
                                        AddConfigOption(project, config_name, group_block.key, name, value,
                                                        option_definition, file_obj)
                                    break

                            else:
                                print("Unknown option: " + option_block.key)
                else:
                    print("Unknown group: " + group_block.key)


# maybe make a configuration options class?
# and all the items be keys or groups
def ParseDefFile(def_file):
    definitions = DefinitionsFile(def_file.key)

    for def_group in def_file.items:

        if def_group.key == "Version":
            definitions.SetVersion(def_group.values[0])
            continue

        # maybe add an option in the def file for changing it?
        # like adding the output name next to the group name?
        # example: "$Compiler"  "ClCompile" {}
        definitions.AddGroup(def_group.key)

        for def_key in def_group.items:
            config_option = ConfigOption(def_key.key)

            for option in def_key.items:

                if option.key == "type":
                    config_option.type = option.values[0]

                elif option.key == "ordinals":
                    config_option.type = "ordinals"
                    for ordinal_option in option.items:
                        config_option.AddOrdinalOption(ordinal_option.key, ordinal_option.values[0])

                elif option.key == "output":
                    config_option.output = option.values[0]

                # idfk
                elif option.key == "globalproperty":
                    config_option.global_property = option.values[0]

                # add a slash to the end of the value
                elif option.key == "AppendSlash":
                    config_option.append_slash = option.values[0]

                # fix the path seperators if needed
                elif option.key == "fixslashes":
                    config_option.fix_slashes = option.values[0]

                # change to "ReplaceCommaWithSemicolon"?
                elif option.key == "PreferSemicolonNoComma":
                    config_option.prefer_semicolon_no_comma = option.values[0]

                # change to "ReplaceSpaceWithSemicolon"?
                elif option.key == "PreferSemicolonNoSpace":
                    config_option.prefer_semicolon_no_space = option.values[0]

                # changes bools to the opposite value
                elif option.key == "invertoutput":
                    config_option.invert_output = option.values[0]

                # in the def file, but the key is different so this is never used
                elif option.key == "alias":
                    config_option.alias = option.values[0]

                # option can also be called this
                elif option.key == "legacy":
                    config_option.legacy = option.values[0]

            # and now add that key to the Definitions Object
            definitions.AddOption(def_group.key, config_option)

    return definitions


def ReplaceMacros(string, macros, macros_required={}):
    if "$" in string:
        # go through all the known macros and check if each one is in the value
        for macro, macro_value in macros.items():
            if macro in string:
                string_split = string.split(macro)
                # should use os path join or something if it has os.sep in the macro and/or string
                string = macro_value.join(string_split)

        for macro, macro_value in macros_required.items():
            if macro in string:
                string_split = string.split(macro)
                # should use os path join or something if it has os.sep in the macro and/or string
                string = macro_value.join(string_split)

    return string


def WriteDependencyList():
    pass


def ParseProject(project_script_path, base_macros, base_conds, definitions):
    project_filename = project_script_path.rsplit(os.sep, 1)[1]
    project_name = project_filename.rsplit(".", 1)[0]

    project_dir = os.path.join(base_macros["$ROOTDIR"], project_script_path.rsplit(os.sep, 1)[0])

    project_path = os.path.join(project_dir, project_filename)

    project = Project(project_name, project_dir, base_macros, base_conds)

    project.crc_list[project_filename] = MakeCRC(project_path)

    if base.FindCommand("/verbose"):
        print("Reading: " + project_filename)

    project_file = ReadFile(project_path)

    if base.FindCommand("/verbose"):
        print("Parsing: " + project_filename)
    else:
        print("Parsing: " + project.name)

    ParseProjectFile(project_file, project, definitions, 0)

    # dependency_list = []
    # dependency_list.extend( project.libraries )
    # will add more later

    # WriteDependencyList( dependency_list ) # change this to dependencies

    return project


def CRCCheck(root_dir, project_path):
    project_crc_path = os.path.join(root_dir, project_path + "_crc")

    if os.sep in project_path:
        project_path = project_path.rsplit(os.sep, 1)[0]

    project_dir = os.path.join(root_dir, project_path) + os.sep

    # open the crc file if it exists,
    # run MakeCRC on every file there
    # and check if it matches what MakeCRC returned
    if os.path.isfile(project_crc_path):
        crc_file = ReadFile(project_crc_path)  # i could use this for it as well lmao

        for crc_line in crc_file:
            project_crc = crc_line.key
            project_file_path = os.path.join(project_dir, crc_line.values[0])

            if project_crc != MakeCRC(project_file_path):
                print("Invalid: " + crc_line.values[0] + "_crc")
                return True

        return False
    else:
        print("CRC File does not exist")
        return True


# Source: https://bitbucket.org/prologic/tools/src/tip/md5sum
def MakeCRC(filename):
    hash = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(128 * hash.block_size), b""):
            hash.update(chunk)
    return hash.hexdigest()


def MakeCRCFile(project_path, crc_list):
    project_path += "_crc"
    with open(project_path, mode="w", encoding="utf-8") as crc_file:
        for project_script_path, crc in crc_list.items():
            crc_file.write(crc + " " + project_script_path + "\n")

    return
