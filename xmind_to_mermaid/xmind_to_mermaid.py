#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = []
# ///
"""
Convert XMind files into Mermaid diagrams.

By default the script emits Mermaid mindmap syntax. It can also emit a
flowchart representation when you need fully quoted node labels.

Usage:
./xmind_to_mermaid/xmind_to_mermaid.py --input roadmap.xmind
./xmind_to_mermaid/xmind_to_mermaid.py --input roadmap.xmind --output roadmap.mmd
./xmind_to_mermaid/xmind_to_mermaid.py --input roadmap.xmind --output roadmap.html --output-format html
./xmind_to_mermaid/xmind_to_mermaid.py --input roadmap.xmind --sheet 1
./xmind_to_mermaid/xmind_to_mermaid.py --input roadmap.xmind --sheet "Architecture"
./xmind_to_mermaid/xmind_to_mermaid.py --input roadmap.xmind --diagram flowchart
./xmind_to_mermaid/xmind_to_mermaid.py --input roadmap.xmind --list-sheets
./xmind_to_mermaid/xmind_to_mermaid.py -v --input roadmap.xmind
"""
from __future__ import annotations

import html
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from dataclasses import dataclass, field
from pathlib import Path


class ConversionError(Exception):
    """Raised when an XMind file cannot be converted."""


@dataclass
class Topic:
    title: str
    children: list[Topic] = field(default_factory=list)


@dataclass
class Sheet:
    title: str
    root_topic: Topic


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
        ],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--input", required=True, type=Path, help="Path to the source .xmind file")
    parser.add_argument("-o", "--output", type=Path, help="Write Mermaid output to this file instead of stdout")
    parser.add_argument(
        "--output-format",
        choices=("mermaid", "html"),
        help="Output format. Defaults to mermaid, or html when --output ends with .html",
    )
    parser.add_argument(
        "-s",
        "--sheet",
        help="Sheet to export, using either a 1-based index or an exact sheet title",
    )
    parser.add_argument(
        "--diagram",
        choices=("mindmap", "flowchart"),
        default="mindmap",
        help="Mermaid diagram type to generate (default: %(default)s)",
    )
    parser.add_argument(
        "--list-sheets",
        action="store_true",
        help="List all available sheets in the XMind file and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


def normalize_title(title):
    cleaned_title = re.sub(r"\s+", " ", (title or "").strip())
    return cleaned_title or "Untitled"


def local_name(tag):
    return tag.rsplit("}", maxsplit=1)[-1]


def find_direct_child(element, child_name):
    for child in element:
        if local_name(child.tag) == child_name:
            return child
    return None


def find_first_descendant(element, child_name):
    for child in element.iter():
        if local_name(child.tag) == child_name:
            return child
    return None


def read_xmind_sheets(input_path):
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    logging.info("Reading XMind file: %s", input_path)
    try:
        with zipfile.ZipFile(input_path) as archive:
            names = set(archive.namelist())
            if "content.json" in names:
                logging.debug("Detected modern XMind content.json format")
                return parse_json_sheets(json.loads(archive.read("content.json").decode("utf-8")))
            if "content.xml" in names:
                logging.debug("Detected legacy XMind content.xml format")
                return parse_xml_sheets(archive.read("content.xml"))
    except zipfile.BadZipFile:
        logging.debug("Input is not a zip archive, trying direct JSON/XML parsing")

    text_content = input_path.read_text(encoding="utf-8")
    stripped_content = text_content.lstrip()
    if stripped_content.startswith("{") or stripped_content.startswith("["):
        logging.debug("Detected direct JSON mindmap export format")
        return parse_json_sheets(json.loads(text_content))
    if stripped_content.startswith("<"):
        logging.debug("Detected direct XML mindmap export format")
        return parse_xml_sheets(text_content.encode("utf-8"))

    raise ConversionError("Unsupported input: expected XMind zip archive or direct JSON/XML export")


def extract_json_sheet_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("sheets", "sheet"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        if "rootTopic" in payload:
            return [payload]
    raise ConversionError("Unsupported content.json structure")


def parse_json_sheets(payload):
    sheets = [parse_json_sheet(item, index) for index, item in enumerate(extract_json_sheet_items(payload), start=1)]
    if not sheets:
        raise ConversionError("The XMind file does not contain any sheets")
    return sheets


def parse_json_sheet(sheet_data, index):
    if not isinstance(sheet_data, dict):
        raise ConversionError(f"Invalid sheet payload at index {index}")

    root_topic_data = sheet_data.get("rootTopic")
    if not isinstance(root_topic_data, dict):
        raise ConversionError(f"Sheet {index} does not contain a root topic")

    return Sheet(
        title=normalize_title(sheet_data.get("title") or f"Sheet {index}"),
        root_topic=parse_json_topic(root_topic_data),
    )


def is_topic_dict(value):
    return isinstance(value, dict) and (value.get("class") == "topic" or "title" in value or "children" in value)


def extract_json_child_topics(container):
    child_topics = []
    if isinstance(container, list):
        for item in container:
            if is_topic_dict(item):
                child_topics.append(item)
                continue
            child_topics.extend(extract_json_child_topics(item))
    elif isinstance(container, dict):
        if is_topic_dict(container):
            child_topics.append(container)
        else:
            for value in container.values():
                child_topics.extend(extract_json_child_topics(value))
    return child_topics


def parse_json_topic(topic_data):
    if not isinstance(topic_data, dict):
        raise ConversionError("Encountered invalid topic structure in content.json")

    children_data = topic_data.get("children", {})
    child_topics = extract_json_child_topics(children_data)
    return Topic(
        title=normalize_title(topic_data.get("title")),
        children=[parse_json_topic(child_topic) for child_topic in child_topics],
    )


def parse_xml_sheets(xml_bytes):
    root = ET.fromstring(xml_bytes)
    sheet_elements = [element for element in root if local_name(element.tag) == "sheet"]
    if not sheet_elements and local_name(root.tag) == "sheet":
        sheet_elements = [root]

    if not sheet_elements:
        raise ConversionError("The XMind file does not contain any sheets")

    return [parse_xml_sheet(sheet_element, index) for index, sheet_element in enumerate(sheet_elements, start=1)]


def parse_xml_sheet(sheet_element, index):
    title = normalize_title(sheet_element.attrib.get("title") or f"Sheet {index}")
    root_topic_element = find_direct_child(sheet_element, "topic") or find_first_descendant(sheet_element, "topic")
    if root_topic_element is None:
        raise ConversionError(f"Sheet {index} does not contain a root topic")

    return Sheet(title=title, root_topic=parse_xml_topic(root_topic_element))


def parse_xml_topic(topic_element):
    title_element = find_direct_child(topic_element, "title")
    title = normalize_title(
        topic_element.attrib.get("title") or (title_element.text if title_element is not None else "")
    )

    child_topics = []
    children_element = find_direct_child(topic_element, "children")
    if children_element is not None:
        for container in children_element:
            container_name = local_name(container.tag)
            if container_name == "topic":
                child_topics.append(parse_xml_topic(container))
                continue
            if container_name != "topics":
                continue
            for child_topic_element in container:
                if local_name(child_topic_element.tag) == "topic":
                    child_topics.append(parse_xml_topic(child_topic_element))

    return Topic(title=title, children=child_topics)


def select_sheets(sheets, selection):
    if selection is None:
        return sheets

    normalized_selection = selection.strip()
    if normalized_selection.isdigit():
        index = int(normalized_selection)
        if index < 1 or index > len(sheets):
            raise ConversionError(f"Sheet index out of range: {index}")
        return [sheets[index - 1]]

    exact_matches = [sheet for sheet in sheets if sheet.title == normalized_selection]
    if exact_matches:
        return exact_matches

    casefold_matches = [sheet for sheet in sheets if sheet.title.casefold() == normalized_selection.casefold()]
    if len(casefold_matches) == 1:
        return casefold_matches

    raise ConversionError(f"Could not find a sheet named: {selection}")


def format_sheet_list(sheets):
    return "\n".join(f"{index}. {sheet.title}" for index, sheet in enumerate(sheets, start=1))


def escape_mermaid_label(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def mindmap_node_id(sheet_index, node_index):
    return f"sheet_{sheet_index}_mindmap_node_{node_index}"


def render_topic_as_mindmap(topic, sheet_index, node_counter, depth):
    node_id = mindmap_node_id(sheet_index, node_counter[0])
    node_counter[0] += 1

    lines = [f'{"  " * depth}{node_id}["{escape_mermaid_label(topic.title)}"]']
    for child in topic.children:
        lines.extend(render_topic_as_mindmap(child, sheet_index, node_counter, depth + 1))
    return lines


def render_sheet_as_mindmap(sheet, sheet_index):
    lines = ["mindmap"]
    node_counter = [1]
    lines.extend(render_topic_as_mindmap(sheet.root_topic, sheet_index, node_counter, 1))
    return "\n".join(lines)


def flowchart_node_id(sheet_index, node_index):
    return f"sheet_{sheet_index}_node_{node_index}"


def render_topic_as_flowchart(topic, sheet_index, node_counter, lines, parent_id=None):
    node_id = flowchart_node_id(sheet_index, node_counter[0])
    node_counter[0] += 1

    lines.append(f'    {node_id}["{escape_mermaid_label(topic.title)}"]')
    if parent_id is not None:
        lines.append(f"    {parent_id} --> {node_id}")

    for child in topic.children:
        render_topic_as_flowchart(child, sheet_index, node_counter, lines, parent_id=node_id)


def render_sheet_as_flowchart(sheet, sheet_index):
    lines = ["flowchart TD", f'    subgraph sheet_{sheet_index}["{escape_mermaid_label(sheet.title)}"]']
    node_counter = [1]
    render_topic_as_flowchart(sheet.root_topic, sheet_index, node_counter, lines)
    lines.append("    end")
    return "\n".join(lines)


def render_sheets(sheets, diagram):
    if diagram == "mindmap":
        return "\n\n".join(render_sheet_as_mindmap(sheet, index) for index, sheet in enumerate(sheets, start=1))
    if diagram == "flowchart":
        return "\n\n".join(render_sheet_as_flowchart(sheet, index) for index, sheet in enumerate(sheets, start=1))
    raise ConversionError(f"Unsupported Mermaid diagram type: {diagram}")


def resolve_output_format(output_path, output_format):
    if output_format is not None:
        return output_format
    if output_path is not None and output_path.suffix.lower() == ".html":
        return "html"
    return "mermaid"


def render_embedded_html(mermaid_source, title):
    escaped_title = html.escape(title)
    escaped_mermaid_source = html.escape(mermaid_source)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #ffffff;
      --fg: #1f2937;
      --muted: #6b7280;
      --panel: #f8fafc;
      --border: #d1d5db;
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0f172a;
        --fg: #e5e7eb;
        --muted: #94a3b8;
        --panel: #111827;
        --border: #334155;
      }}
    }}

    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: var(--bg);
      color: var(--fg);
    }}

    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: 1.8rem;
    }}

    p {{
      color: var(--muted);
      margin: 0 0 24px;
    }}

    .diagram-wrapper,
    details {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 20px;
      overflow: auto;
    }}

    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    }}
  </style>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true }});
  </script>
</head>
<body>
  <main>
    <h1>{escaped_title}</h1>
    <p>Embedded Mermaid export generated by xmind_to_mermaid.py.</p>
    <section class="diagram-wrapper">
      <pre class="mermaid">{escaped_mermaid_source}</pre>
    </section>
    <details>
      <summary>Show Mermaid source</summary>
      <pre>{escaped_mermaid_source}</pre>
    </details>
  </main>
</body>
</html>"""


def write_output(output_path, content):
    if output_path is None:
        print(content)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{content}\n", encoding="utf-8")
    logging.info("Wrote Mermaid output to %s", output_path)


def main(args):
    sheets = read_xmind_sheets(args.input)
    logging.info("Loaded %s sheets", len(sheets))

    if args.list_sheets:
        print(format_sheet_list(sheets))
        return

    selected_sheets = select_sheets(sheets, args.sheet)
    logging.info("Exporting %s sheet(s) as %s", len(selected_sheets), args.diagram)

    mermaid_output = render_sheets(selected_sheets, args.diagram)
    output_format = resolve_output_format(args.output, args.output_format)
    if output_format == "html":
        sheet_label = selected_sheets[0].title if len(selected_sheets) == 1 else f"{len(selected_sheets)} sheets"
        rendered_output = render_embedded_html(mermaid_output, f"{args.input.stem} - {sheet_label}")
    else:
        rendered_output = mermaid_output
    write_output(args.output, rendered_output)


if __name__ == "__main__":
    arguments = parse_args()
    setup_logging(arguments.verbose)
    try:
        main(arguments)
    except (ConversionError, FileNotFoundError, zipfile.BadZipFile, json.JSONDecodeError, ET.ParseError) as exc:
        logging.error(str(exc))
        sys.exit(1)
