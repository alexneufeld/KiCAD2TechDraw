"""
This script converts .kicad_wks files to FreeCAD TechDraw compatible .svg
"""

import os
from lisp_like_parser import parse
from pprint import pprint

# A size paper dimensions in mm
iso_pages = {
    "A2": [549,420],
    "A3": [420,297],
    "A4": [297,210],
    "A4-portrait": [210,297]
}

# map KICAD's abbreviations for input fields to equivalent FreeCAD norms
eq_editable = {
    "%C0":  "Comment 1",
    "%C1":  "Comment 2",
    "%C2":  "Comment 3",
    "%C3":  "Comment 4",
    "%S/%N": "SheetNo",
    "%T":   "Title",
    "%Y":   "Organization",
    "%R":   "Revision",
    "%D":   "Date",

}

def to_svg(ast):
    # ast transformer to convert tokens to svg
    result = ""
    cmd = ast[0]
    if cmd == "page_layout":
        result += f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!-- Generated with KiCAD2TechDraw: https://github.com/alexneufeld/KiCAD2TechDraw -->
<!-- Based on templates created by the KICAD developers: https://gitlab.com/kicad/libraries/kicad-templates -->

<svg
    xmlns="http://www.w3.org/2000/svg" version="1.1"
    xmlns:freecad="http://www.freecadweb.org/wiki/index.php?title=Svg_Namespace"
    width="{PAGE_SIZE[0]}mm"
    height="{PAGE_SIZE[1]}mm"
    viewBox="0 0 {PAGE_SIZE[0]} {PAGE_SIZE[1]}">\n"""
        for sub_ast in ast[1:]:
            result += to_svg(sub_ast)
        result += "</svg>\n"
    elif cmd == "setup":
        global LINE_WIDTH
        LINE_WIDTH = ast[2][1]
        global LEFT_MARGIN
        LEFT_MARGIN = ast[4][1]
        global RIGHT_MARGIN
        RIGHT_MARGIN = ast[5][1]
        global TOP_MARGIN
        TOP_MARGIN = ast[6][1]
        global BOTTOM_MARGIN
        BOTTOM_MARGIN = ast[7][1]
    elif cmd == "line":
        x1, y1 = parse_coord(ast[2])
        x2, y2 = parse_coord(ast[3])
        linewidth = ast[4][1]#*LINE_WIDTH
        ident = ast[1][1]
        # NOTE - 75% of spec'd linewidth seems to produce the most accurate results
        result += f'<line id="{ident}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="stroke: black; stroke-width: {0.75*linewidth}pt; stroke-linecap: round; stroke-linejoin:round;"/>\n'
    elif cmd == "rect":
        x1, y1 = parse_coord(ast[2])
        x2, y2 = parse_coord(ast[3])
        if x2 > x1:
            width=x2-x1
            xs = x1
        else:
            width=x1-x2
            xs=x2
        if y2 > y1:
            height=y2-y1
            ys = y1
        else:
            height=y1-y2
            ys = y2
        linewidth = ast[4][1]#*LINE_WIDTH
        rect_name = ast[1][1]
        result += f'<rect x="{xs}" y="{ys}" width="{width}" height="{height}" id="{rect_name}" style="stroke: black; stroke-width: {0.75*linewidth}pt; stroke-linecap: round; stroke-linejoin: round; fill: none;"/>\n'
    elif cmd == "tbtext":
        # need to handle either static or editable text
        # quoted sentences also get split to multiple tokens 
        # It's all just a mess
        actual_text = []
        for subitem in ast[1:]:
            if type(subitem) != list:
                actual_text.append(str(subitem))
            else:
                break
        text_str = " ".join(actual_text).strip('"')
        rem = ast[len(actual_text)+1:]
        #print(text_str)
        xpos, ypos = [0,0]
        text_justify = "left"
        text_height = 3.14159263
        text_id = "No_ID"
        for item in rem:
            if item[0] == "pos":
                xpos,ypos = parse_coord(item)
            elif item[0] == "justify":
                text_justify = item[1]
            elif item[0] == "font":
                text_height = item[2][2]
            elif item[0] == "name":
                text_id = item[1]
        if text_justify == "left":
            anchor = "start"
        else:
            anchor = "middle"
        # static text
        if not text_str.startswith("%"):
            # assign defaults
            # NOTE: dy="{0.35*text_height}pt" compensates for differences between osifont and KiCAD's typical font geometry
            result += f'<text x="{xpos}" y="{ypos}" transform="translate(0,{0.35*text_height})" id="{text_id}" style="font-size: {text_height}pt; text-anchor: {anchor}; fill: black; font-family: osifont">{text_str}</text>\n'
        else: # editable text
            result += f'<text freecad:editable="{eq_editable[text_str]}" x="{xpos}" y="{ypos}" transform="translate(0,{0.35*text_height})" id="{text_id}" style="font-size: {text_height}pt; text-anchor: {anchor}; fill: black; font-family: osifont"><tspan>x</tspan></text>\n'
    elif cmd == "polygon":
        path_id = "none"
        path_rotate = "0"
        path_line = 0.35
        thru_list = []
        xp, yp = [0,0]
        for item in ast[1:]:
            if item[0] == "name":
                path_id = item[1]
            elif item[0] == "rotate":
                path_rotate = 360-item[1]
            elif item[0] == "pos":
                xp, yp = parse_coord(item)
            elif item[0] == "linewidth":
                path_line = item[1]
            elif item[0] == "pts":
                for pt in item[1:]:
                    thru_list.append([pt[1],pt[2]])
            plist_str = ""
            for xy in thru_list:
                plist_str += str(xy[0]) + "," + str(xy[1]) + " "
        result += f'<g transform="translate({xp},{yp})"><polygon id="{path_id}" transform="rotate({path_rotate})" points="{plist_str}" style="fill: solid black; stroke-width: {0.75*path_line}pt; stroke-linecap: round; stroke-linejoin: round;"/></g>\n'
    return result

def parse_coord(c):
    # coordinates are specified relative to any one of the 4 page corners
    # This is an 'interesting' design choice.
    if len(c) == 4:
        rel = c[3]
    elif len(c) == 3:
        rel = "rbcorner"
    xi = c[1]
    yi = c[2]
    if rel == "ltcorner":
        x = xi+LEFT_MARGIN
        y = yi+TOP_MARGIN
    elif rel == "lbcorner":
        x = xi+LEFT_MARGIN
        y = -1*yi+PAGE_SIZE[1]-BOTTOM_MARGIN
    elif rel == "rtcorner":
        x = -1*xi+PAGE_SIZE[0]-RIGHT_MARGIN
        y = yi+TOP_MARGIN
    elif rel == "rbcorner":
        x = PAGE_SIZE[0]-xi-RIGHT_MARGIN
        y = -1*yi+PAGE_SIZE[1]-BOTTOM_MARGIN
    return [x,y]

if __name__ == "__main__":
    for srcfile in os.listdir("kicad-templates/Worksheets"):
        # only works with some of the tempaltees for now
        if not srcfile.startswith("A"):
            continue
        pagetype = srcfile.split("_")[0]
        global PAGE_SIZE
        PAGE_SIZE = iso_pages[pagetype]
        # open the file and get the token list
        f = open(os.path.join("kicad-templates/Worksheets",srcfile),'r')
        contents = f.read()
        x = parse(contents)
        #pprint(x)
        svgstr = to_svg(x)
        outfile = os.path.join("out",srcfile[:-10]+".svg")
        with open(outfile,'w') as g:
            g.write(svgstr)
        print("Successfully exported to "+outfile)