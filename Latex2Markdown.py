#!/usr/bin/python3

#
# Latex2Markdown
#
# Copyright (C) 2021 Gabriel Ferreira
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import argparse
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()
re_match_html_author = re.compile("""meta name="author" content="(.*)" />""")
re_match_html_title = re.compile("""<title>(.*)</title>""")


def latex_to_html_via_pandoc(source_file):
    # Get source file directory path
    source_dir = os.path.dirname(source_file)

    # Split the content type from it, determine the target directory path and layout type
    content_type = os.path.basename(source_dir)
    target_dir = "_%s" % content_type
    layout = "post" if content_type in ["posts", "news"] else "page"

    # Path to the output file
    output_file = source_file.replace(".tex", ".html").replace(source_dir, target_dir)

    # Latex to html
    command = """pandoc --number-sections --mathjax -f latex -t html -s"""
    command = command.split(" ")

    # Load references from bib file if it exists
    bibliography = source_file.replace(".tex", ".bib")
    if os.path.exists(bibliography):
        command.append("--bibliography=%s" % bibliography)  # use external bib file or not

    command.append("-o")
    command.append(output_file)  # output path
    command.append(source_file)  # source path

    # Run pandoc
    try:
        subprocess.check_output(command)
    except Exception as e:
        raise Exception("Error during pandoc conversion of %s: %s" % (source_file, e))

    # Open the html file and get only contents to let jekyll handle style, links, etc
    with open(output_file, "r", encoding="utf-8") as f:
        contents = f.read()

        # extract authors and title
        authors = re_match_html_author.findall(contents)
        author = authors[0]
        authors.pop(0)
        while len(authors) > 0:
            author += ", " + authors[0]
            authors.pop(0)
        del authors
        title = re_match_html_title.findall(contents)[0]

        # Remove unnecessary header and trailer
        contents = contents.split("</header>")[1]
        contents = contents.split("</body>")[0]

        # Inline post if news
        is_inline = "inline: true\n" if content_type == "news" and len(contents) < 100 else ""

    # Rewrite file with markdown header
    with open(output_file, "w", encoding="utf-8") as f:
        # Write markdown header
        f.write("""---\nlayout: %s\nauthor: "%s"\ntitle: "%s"\n%s---""" % (layout, author, title, is_inline))

        # Write stripped down html
        f.write(contents)


def main():
    parser = argparse.ArgumentParser(description='Produce Jekyll posts from LaTeX sources.')
    parser.add_argument('--serve', action="store_true", default=False,
                        help='use "--serve True" to start the jekyll development server after processing files', )
    args = parser.parse_args()

    if not os.path.exists("latex"):
        print("No latex files to parse")
        exit(0)

    # Scan for tex files
    for content_type in os.scandir("latex"):
        target_dir = "_%s" % content_type.name
        os.makedirs(target_dir, exist_ok=True)
        for content in os.scandir("latex/%s" % content_type.name):
            if content.name.endswith(".tex"):
                # Process them
                executor.submit(latex_to_html_via_pandoc, content.path)

    # Run jekyll to rebuild the site
    if not args.serve:
        subprocess.check_output("bundle exec jekyll build".split(" "))
    else:
        subprocess.check_output("bundle exec jekyll serve".split(" "))
    print("We are done here")


main()
