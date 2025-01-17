# ---------------------------------------------------------------------
# Purpose: Be a pretty much exact copy of Valve Project Creator
#   except i strongly doubt i will even come close to finishing lol
# 
# Written by Demez
# 
# Days worked on:
#   07/02/2019
#   07/03/2019
#   07/04/2019
#   07/05/2019
#   07/06/2019
#   07/07/2019
#   07/08/2019
#   07/09/2019 - finished parsing vgc files with ReadFile() (it can also read keyvalues)
#   07/10/2019
#   07/11/2019
#   07/12/2019
#   07/13/2019
#   07/14/2019
# ---------------------------------------------------------------------
import argparse
import os
import sys
from pathlib import Path

import PyQPC_Parser as parser
import PyQPC_Writer as writer


def SetupDefines(parsed_cmds):
    macros = {}
    conditionals = {}

    if sys.platform == "win32":
        conditionals["$WINDOWS"] = 1
        macros += {
            "$_DLL_EXT": ".dll",
            "$_STATICLIB_EXT": ".lib",
            "$_IMPLIB_EXT": ".lib",
            "$_EXE_EXT": ".exe"
        }

        # for win64 just use /win64 from the commmand line for now
        # if you ever finish this pile of shit
        # change it so you can have x86 and x64 in the same project
        if parsed_cmds.platform == 'win64':
            conditionals["$WIN64"] = 1
            macros["$PLATFORM"] = "win64"
        else:
            conditionals["$WIN32"] = 1
            macros["$PLATFORM"] = "win32"

    # fix this, these are pretty much for linux only
    elif sys.platform.startswith('linux'):
        conditionals += {
            "$POSIX": 1,
            "$LINUXALL": 1,
            "$GL": 1
        }

        macros += {
            "$POSIX": "1",
            "$_POSIX": "1",
            "$_DLL_EXT": ".so",
            "$_EXTERNAL_DLL_EXT": ".so",
            "$_STATICLIB_EXT": ".a",
            "$_EXTERNAL_STATICLIB_EXT": ".a",
            "$_IMPLIB_EXT": ".so",
            "$_EXTERNAL_IMPLIB_EXT": ".so",
            "$_IMPLIB_PREFIX": "lib",
            "$_IMPLIB_DLL_PREFIX": "lib",
            "$_EXE_EXT": "",
            "$_SYM_EXT": ".dbg",
        }

        if parsed_cmds.platform == 'linux64':
            conditionals["$POSIX64"] = 1
            macros["$PLATFORM"] = "linux64"
        else:
            conditionals["$POSIX32"] = 1
            macros["$PLATFORM"] = "linux32"

    macros["$QUOTE"] = '"'
    # base_macros[ "$BASE" ] = ''

    # idk what this does, though in vpc it apparently forces all projects to regenerate if you change it
    # i've never changed it before
    # base_macros[ "$InternalVersion" ] = "104"
    # base_conditionals[ "$InternalVersion" ] = 104

    # also apparently a macro doesn't need to be in caps? ffs
    macros["$INTERNALVERSION"] = "104"
    conditionals["$INTERNALVERSION"] = 104

    return macros, conditionals


def ParseArgs():
    cmd_parser = argparse.ArgumentParser("Turn VPC projects into VS projects")

    # maybe move handling command line parameters to different functions?
    cmd_parser.add_argument('path', default=Path().absolute(),
                            help='directory containing .vgc defs')
    cmd_parser.add_argument('-v', '--verbose', action='store_true')
    cmd_parser.add_argument('-l', '--legacyoptions', action='store_true')
    cmd_parser.add_argument('-w', '--hidewarnings', action='store_true')
    cmd_parser.add_argument('-c', '--checkfiles', action='store_true')
    cmd_parser.add_argument('-f', '--force', action='store_true', dest='force')
    cmd_parser.add_argument('conditionals', nargs='*', type=str)
    cmd_parser.add_argument('--type', choices=["vstudio", "vscode", "make"])
    cmd_parser.add_argument('--name', type=str)
    cmd_parser.add_argument('--add', nargs='+', type=str)
    cmd_parser.add_argument('--remove', nargs='+', type=str)
    cmd_parser.add_argument('--platform', choices=['win32', 'win64', 'linux32', 'linux64'])

    return cmd_parser.parse_args()


if __name__ == "__main__":

    print("----------------------------------------------------------------------------------")
    print(" PyQPC " + ' '.join(sys.argv[1:]))
    print("----------------------------------------------------------------------------------")

    all_groups = {}
    all_projects = {}

    project_type = None

    parsed = ParseArgs()

    base_macros, base_conditionals = SetupDefines(parsed)

    # now start the recursion with default.vgc, which i just set to be in the same folder as this
    rootdir = parsed.path

    if parsed.verbose:
        print("Reading: " + rootdir / "default.vgc")

    base_file = parser.ReadFile(rootdir / "default.vgc", **vars(parsed))

    base_macros["$ROOTDIR"] = str(rootdir)
    definitions_file_path = parser.ParseBaseFile(base_file, base_macros, base_conditionals, parsed.conditionals,
                                                 all_projects, all_groups)

    base_macros["$ROOTDIR"] = os.path.normpath(base_macros["$ROOTDIR"])
    definitions_file_path = os.path.normpath(definitions_file_path)

    # TODO: check the cmd options if help was set 

    # maybe report any unknown conditionals remaining? 

    if definitions_file_path:
        definitions_file = parser.ReadFile(definitions_file_path)
    else:
        raise ValueError("Definitions file needed for configuration options is undefined" +
                         "Set this with $Definitions \"Path\" in default.vgc")

    definitions = parser.ParseDefFile(definitions_file[0])

    # setup any defines from the command line for what projects and/or groups we want

    # AddedProjectsOrGroups
    add_proj_and_grps = parsed.add
    # RemovedProjectsOrGroups
    rm_proj_and_grps = parsed.remove

    # TODO: figure out how vpc handles these and recreate it here
    # might come waaay later since it's very low priority
    # FindCommandValues( "*" ) # add a project and all projects that depend on it.
    # FindCommandValues( "@" ) # add a project and all projects that it depends on.
    # Use /h spew final target build set only (no .vcproj created). - what?

    # Now go through everything and add all the project scripts we want to this list
    # why did i make it so damn condensed
    # actually should i make this contain the project name and the project script as a dictionary? like in VPC?
    project_script_list = []

    if add_proj_and_grps:
        for added_item in add_proj_and_grps:
            if added_item in all_groups:

                for project in all_groups[added_item]:
                    # if project isn't being removed
                    if (project.lower()) not in rm_proj_and_grps:
                        for script in all_projects[project.casefold()]:
                            # only add if this project isn't empty AND it isn't in the project list already
                            if (script != '') and (not script in project_script_list):
                                project_script_list.append(script)

            elif (added_item in all_projects) and (added_item not in rm_proj_and_grps):

                # if project isn't being removed
                if (added_item.lower()) not in rm_proj_and_grps:
                    for script in all_projects[added_item.casefold()]:
                        # only add if this project isn't empty AND it isn't in the project list already
                        if (script != '') and (not script in project_script_list):
                            project_script_list.append(script)
            else:
                print("hey this item doesn't exist: " + added_item)
    else:
        print("add some projects or groups ffs")

    # --------------------------------------------------------------------------------------

    print("")
    project_path_list = []
    for project_path in project_script_list:

        # only run if the crc check fails or if the user force creates the projects
        if parser.CRCCheck(base_macros["$ROOTDIR"], project_path) or parsed.force:

            # OPTIMIZATION IDEA:
            # every time you call ReadFile(), add the return onto some dictionary, keys are the absolute path, values are the returns
            # and then scan that dictionary whenever you reach an include, and then just grab it from the last to parse again
            # so you don't slow it down with re-reading it for no damn reason

            # another idea:
            # make a ParseConfigGroup() function, so you can parse config groups recursively
            # would also nead to tweak ParseDefFile() to use ParseDefOption() and ParseDefGroup() as well

            project = parser.ParseProject(project_path, base_macros, base_conditionals, definitions)

            project.crc_list[definitions_file_path] = parser.MakeCRC(definitions_file_path)

            parser.MakeCRCFile(os.path.join(base_macros["$ROOTDIR"], project_path), project.crc_list)

            if parsed.verbose:
                print("Parsed: " + project.name)

            # i might need to get a project uuid from this, oof
            # except i can't actually do that, because of crc checks
            writer.CreateProject(project, project_type)

            del project
            print("")

        else:
            # TODO: fix this for if the project script is in the root dir
            project_filename = project_path.rsplit(os.sep, 1)[1]
            print("Valid: " + project_filename + "_crc\n")

        project_path_list.append(project_path.rsplit(".", 1)[0])

    if parsed.type == 'vstudio':
        writer.MakeSolutionFile(project_type, project_path_list, rootdir,
                                parsed.name)

    # would be cool to add a timer here that would be running on another thread
    # if the cmd option "/benchmark" was specified, though that might be used as a conditional
    print("----------------------------------")
    print(" Finished")
    print("----------------------------------\n")
