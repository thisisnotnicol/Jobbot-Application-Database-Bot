#!/usr/bin/env python3
"""
Enhanced Job Description Formatter for JobBot
Handles perfect bullet formatting and structure preservation for Notion
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

class JobDescriptionFormatter:
    """Advanced formatter for job descriptions with bullet preservation"""

    # Bullet patterns to recognize
    BULLET_PATTERNS = [
        (r'^[•·▪▫◦‣⁃]', 'bullet'),           # Various bullet characters
        (r'^[-–—](?=\s)', 'dash'),            # Dash bullets
        (r'^\*(?=\s)', 'asterisk'),           # Asterisk bullets
        (r'^\d+[\.\)]\s', 'numbered'),        # Numbered lists (1. or 1))
        (r'^[a-z][\.\)]\s', 'lettered'),      # Lettered lists (a. or a))
        (r'^[ivxIVX]+[\.\)]\s', 'roman'),     # Roman numerals
    ]

    # Section header patterns
    SECTION_PATTERNS = [
        (r'^(responsibilities|duties|requirements|qualifications|skills|experience|benefits|perks|about|overview|description|what you.?ll do|what we.?re looking for|nice to have|must have|preferred|minimum|desired|essential|key|core|main|primary|additional|bonus|other|notes?):?\s*$', 'section'),
        (r'^[A-Z][A-Z\s]{2,}:?\s*$', 'caps_header'),  # ALL CAPS headers
        (r'^#+\s+(.+)$', 'markdown_header'),          # Markdown headers
    ]

    def __init__(self):
        self.max_text_length = 2000  # Notion's text field limit
        self.max_block_length = 2000  # Notion's block text limit

    def format_for_notion(self,
                          content: str,
                          soup: Optional[BeautifulSoup] = None,
                          summary: Optional[str] = None) -> Dict[str, Any]:
        """
        Format job description for Notion with perfect structure preservation

        Args:
            content: Plain text job description
            soup: Optional BeautifulSoup parsed HTML
            summary: Optional job summary to prepend

        Returns:
            Dictionary with formatted content for different Notion field types
        """
        result = {
            'rich_text': '',           # For rich text fields (2000 char limit)
            'blocks': [],              # For page content (blocks API)
            'markdown': '',            # Markdown formatted version
            'sections': {},            # Parsed sections
            'bullets': [],             # Extracted bullet points
            'has_structure': False     # Whether structured content was found
        }

        # Process HTML if available for better structure
        if soup:
            structured_content = self._parse_html_structure(soup)
            if structured_content['has_structure']:
                result.update(structured_content)

        # Always process plain text as fallback or primary
        if not result['has_structure']:
            result.update(self._parse_text_structure(content))

        # Add summary if provided
        if summary:
            result = self._add_summary_to_result(summary, result)

        # Create rich text version (truncated for Notion field)
        result['rich_text'] = self._create_rich_text_field(result)

        return result

    def _parse_html_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured content from HTML"""
        blocks = []
        sections = {}
        bullets = []
        current_section = 'Main'
        has_structure = False

        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'div', 'span']):
            # Skip empty elements
            text = element.get_text(strip=True)
            if not text:
                continue

            # Handle headers
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                has_structure = True
                current_section = text
                sections[current_section] = []
                blocks.append(self._create_heading_block(text, int(element.name[1])))

            # Handle lists
            elif element.name in ['ul', 'ol']:
                has_structure = True
                list_items = element.find_all('li', recursive=False)
                for li in list_items:
                    li_text = li.get_text(strip=True)
                    if li_text:
                        bullets.append(li_text)
                        sections.setdefault(current_section, []).append(f"• {li_text}")
                        blocks.append(self._create_bullet_block(li_text))

            # Handle list items not in ul/ol
            elif element.name == 'li' and element.parent.name not in ['ul', 'ol']:
                li_text = element.get_text(strip=True)
                if li_text:
                    bullets.append(li_text)
                    sections.setdefault(current_section, []).append(f"• {li_text}")
                    blocks.append(self._create_bullet_block(li_text))

            # Handle paragraphs
            elif element.name == 'p':
                # Check if it's a bullet-like paragraph
                if self._is_bullet_line(text):
                    has_structure = True
                    clean_text = self._clean_bullet_text(text)
                    bullets.append(clean_text)
                    sections.setdefault(current_section, []).append(f"• {clean_text}")
                    blocks.append(self._create_bullet_block(clean_text))
                else:
                    sections.setdefault(current_section, []).append(text)
                    blocks.append(self._create_paragraph_block(text))

        # Create markdown from sections
        markdown = self._sections_to_markdown(sections)

        return {
            'blocks': blocks,
            'sections': sections,
            'bullets': bullets,
            'markdown': markdown,
            'has_structure': has_structure
        }

    def _parse_text_structure(self, content: str) -> Dict[str, Any]:
        """Parse plain text into structured format"""
        lines = content.split('\n')
        blocks = []
        sections = {}
        bullets = []
        current_section = 'Overview'
        has_structure = False

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Check for section headers
            is_header, header_type = self._is_section_header(line)
            if is_header:
                has_structure = True
                current_section = line.rstrip(':').strip()
                sections[current_section] = []
                blocks.append(self._create_heading_block(current_section, 2))
                i += 1
                continue

            # Check for bullet points
            if self._is_bullet_line(line):
                has_structure = True
                # Collect consecutive bullets
                bullet_group = []
                while i < len(lines) and self._is_bullet_line(lines[i].strip()):
                    if lines[i].strip():
                        clean_text = self._clean_bullet_text(lines[i].strip())
                        bullet_group.append(clean_text)
                        bullets.append(clean_text)
                        sections.setdefault(current_section, []).append(f"• {clean_text}")
                    i += 1

                # Add bullets as blocks
                for bullet in bullet_group:
                    blocks.append(self._create_bullet_block(bullet))
                continue

            # Regular paragraph
            sections.setdefault(current_section, []).append(line)
            blocks.append(self._create_paragraph_block(line))
            i += 1

        # Create markdown
        markdown = self._sections_to_markdown(sections)

        return {
            'blocks': blocks,
            'sections': sections,
            'bullets': bullets,
            'markdown': markdown,
            'has_structure': has_structure
        }

    def _is_bullet_line(self, line: str) -> bool:
        """Check if a line is a bullet point"""
        line = line.strip()
        for pattern, _ in self.BULLET_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

    def _clean_bullet_text(self, line: str) -> str:
        """Remove bullet markers from text"""
        line = line.strip()

        # Remove various bullet patterns
        for pattern, _ in self.BULLET_PATTERNS:
            line = re.sub(pattern, '', line, flags=re.IGNORECASE).strip()

        return line

    def _is_section_header(self, line: str) -> Tuple[bool, Optional[str]]:
        """Check if a line is a section header"""
        line = line.strip()

        for pattern, header_type in self.SECTION_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                return True, header_type

        # Check for short lines that might be headers (e.g., single words in caps)
        if len(line) < 50 and line.isupper() and ' ' not in line.strip():
            return True, 'single_word_caps'

        return False, None

    def _create_heading_block(self, text: str, level: int = 2) -> Dict[str, Any]:
        """Create a Notion heading block"""
        heading_type = f"heading_{min(level, 3)}"  # Notion only supports heading_1, heading_2, heading_3

        return {
            "object": "block",
            "type": heading_type,
            heading_type: {
                "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
                "color": "default"
            }
        }

    def _create_bullet_block(self, text: str) -> Dict[str, Any]:
        """Create a Notion bulleted list item block"""
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
                "color": "default"
            }
        }

    def _create_paragraph_block(self, text: str) -> Dict[str, Any]:
        """Create a Notion paragraph block"""
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
                "color": "default"
            }
        }

    def _sections_to_markdown(self, sections: Dict[str, List[str]]) -> str:
        """Convert sections dictionary to markdown format"""
        markdown_parts = []

        for section_name, content_list in sections.items():
            if not content_list:
                continue

            # Add section header
            markdown_parts.append(f"## {section_name}\n")

            # Add content
            for item in content_list:
                if item.startswith('•'):
                    markdown_parts.append(item)
                else:
                    markdown_parts.append(item)

            markdown_parts.append("")  # Empty line between sections

        return '\n'.join(markdown_parts)

    def _add_summary_to_result(self, summary: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Add summary to the beginning of all formats"""

        # Add summary block
        summary_blocks = [
            self._create_heading_block("📋 Summary", 2),
            self._create_paragraph_block(summary),
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            }
        ]

        result['blocks'] = summary_blocks + result['blocks']

        # Add to markdown
        result['markdown'] = f"## 📋 Summary\n\n{summary}\n\n---\n\n{result['markdown']}"

        # Add to sections
        result['sections'] = {'Summary': [summary], **result['sections']}

        return result

    def _create_rich_text_field(self, result: Dict[str, Any]) -> str:
        """Create a truncated rich text field for Notion property (2000 char limit)"""

        # Priority order: summary + key bullets
        text_parts = []

        # Add summary if in sections
        if 'Summary' in result['sections']:
            text_parts.append("📋 Summary:")
            text_parts.extend(result['sections']['Summary'][:2])  # First 2 lines of summary
            text_parts.append("")

        # Add key responsibilities/requirements
        for section_name in ['Responsibilities', 'Requirements', 'Key Responsibilities', 'What You\'ll Do']:
            if section_name in result['sections']:
                text_parts.append(f"▪ {section_name}:")
                # Add first 3-5 bullets
                for item in result['sections'][section_name][:5]:
                    if len('\n'.join(text_parts)) + len(item) > 1900:
                        break
                    text_parts.append(item)
                text_parts.append("")
                break

        # If still have room, add some bullets
        if len('\n'.join(text_parts)) < 1500 and result['bullets']:
            text_parts.append("▪ Key Points:")
            for bullet in result['bullets'][:5]:
                if len('\n'.join(text_parts)) + len(bullet) > 1900:
                    break
                text_parts.append(f"• {bullet}")

        combined_text = '\n'.join(text_parts)

        # Ensure we don't exceed limit
        if len(combined_text) > 2000:
            combined_text = combined_text[:1997] + "..."

        return combined_text

    def format_simple(self, text: str) -> str:
        """Simple format for basic text display with bullets preserved"""
        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue

            # Standardize bullets
            if self._is_bullet_line(line):
                clean_text = self._clean_bullet_text(line)
                formatted_lines.append(f"• {clean_text}")
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)


# Utility functions for external use

def format_job_description(content: str,
                          soup: Optional[BeautifulSoup] = None,
                          summary: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for formatting job descriptions

    Returns dict with:
    - rich_text: Formatted text for Notion rich text field (2000 char)
    - blocks: List of Notion blocks for page content
    - markdown: Markdown formatted version
    - bullets: List of extracted bullet points
    """
    formatter = JobDescriptionFormatter()
    return formatter.format_for_notion(content, soup, summary)


def extract_key_bullets(content: str, max_bullets: int = 10) -> List[str]:
    """Extract the most important bullet points from job description"""
    formatter = JobDescriptionFormatter()
    result = formatter.format_for_notion(content)

    # Prioritize bullets from key sections
    key_bullets = []

    for section in ['Requirements', 'Responsibilities', 'Qualifications', 'What You\'ll Do']:
        if section in result['sections']:
            for item in result['sections'][section]:
                if item.startswith('•') and len(key_bullets) < max_bullets:
                    key_bullets.append(item[2:].strip())  # Remove bullet marker

    # Add any remaining bullets if needed
    for bullet in result['bullets']:
        if len(key_bullets) >= max_bullets:
            break
        if bullet not in key_bullets:
            key_bullets.append(bullet)

    return key_bullets


def create_notion_blocks(content: str,
                        soup: Optional[BeautifulSoup] = None,
                        summary: Optional[str] = None) -> List[Dict[str, Any]]:
    """Create properly formatted Notion blocks from job description"""
    formatter = JobDescriptionFormatter()
    result = formatter.format_for_notion(content, soup, summary)
    return result['blocks']
