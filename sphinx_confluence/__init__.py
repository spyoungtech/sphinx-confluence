# -*- coding: utf-8 -*-
"""

https://confluence.atlassian.com/display/DOC/Confluence+Storage+Format

"""

from distutils.version import LooseVersion
import os

from docutils import nodes
from docutils.parsers.rst import directives, Directive, roles
from docutils.parsers.rst.directives import images
from docutils.parsers.rst.roles import set_classes

import sphinx
from sphinx.builders.html import JSONHTMLBuilder
from sphinx.directives.code import CodeBlock
from sphinx.locale import _
from sphinx.writers.html import HTMLTranslator
import logging

logger = logging.getLogger(__name__)

def setup_config(config_path, **authentication):
    from yaml import load
    from conf_publisher.confluence_api import create_confluence_api
    from conf_publisher.constants import DEFAULT_CONFLUENCE_API_VERSION as version
    from conf_publisher.auth import parse_authentication
    with open(config_path) as f:
        sc_config = load(f.read())

    sphinx_confluence_url = sc_config.get('url')
    session = parse_authentication(**authentication)
    conf_api = create_confluence_api(version, sphinx_confluence_url, session)

    def update_page(page_dict):
        page_id = page_dict.get('id')
        page_path = page_dict.get('source')
        abspath = os.path.abspath(page_path)
        page_info = conf_api.get_content(page_id)
        page_path = page_info.get('_links').get('webui')
        page_title = page_info.get('title')
        page_short_title = page_title.replace(' ', '')
        page_dict.update({'server_path': page_path,
                          'title': page_title,
                          'short_title': page_short_title,
                          'local_path': abspath})
        if 'pages' in page_dict:
            for page in page_dict['pages']:
                update_page(page)

    for page in sc_config.get('pages'):
        update_page(page)

    return sc_config.get('pages')

def true_false(argument):
    return directives.choice(argument, ('true', 'false'))


def static_dynamic(argument):
    return directives.choice(argument, ('static', 'dynamic'))


class TitlesCache(object):
    titles = {}

    @staticmethod
    def _document_key(document):
        return hash(document)

    @classmethod
    def set_title(cls, document, title):
        cls.titles[cls._document_key(document)] = title

    @classmethod
    def get_title(cls, document):
        return cls.titles.get(cls._document_key(document), None)

    @classmethod
    def has_title(cls, document):
        return cls._document_key(document) in cls.titles


class JSONConfluenceBuilder(JSONHTMLBuilder):
    """For backward compatibility"""

    name = 'json_conf'

    def __init__(self, app):
        super(JSONConfluenceBuilder, self).__init__(app)
        if LooseVersion(sphinx.__version__) >= LooseVersion("1.4"):
            self.translator_class = HTMLConfluenceTranslator
        self.warn('json_conf builder is deprecated and will be removed in future releases')


class HTMLConfluenceTranslator(HTMLTranslator):

    def unimplemented_visit(self, node):
        self.builder.warn('Unimplemented visit is not implemented for node: {}'.format(node))

    def unknown_visit(self, node):
        self.builder.warn('Unknown visit is not implemented for node: {}'.format(node))

    def visit_admonition(self, node, name=''):
        """
        Info, Tip, Note, and Warning Macros

        https://confluence.atlassian.com/conf58/info-tip-note-and-warning-macros-771892344.html

        <ac:structured-macro ac:name="info">
          <ac:parameter ac:name="icon">false</ac:parameter>
          <ac:parameter ac:name="title">This is my title</ac:parameter>
          <ac:rich-text-body>
            <p>
              This is important information.
            </p>
          </ac:rich-text-body>
        </ac:structured-macro>
        """

        confluence_admonition_map = {
            'note': 'info',
            'warning': 'note',
            'attention': 'note',
            'hint': 'tip',
            'tip': 'tip',
            'important': 'warning',
            'error': 'warning',
            'danger': 'warning',
        }

        admonition_type = confluence_admonition_map.get(name, 'info')

        macro = """\
            <ac:structured-macro ac:name="{admonition_type}">
              <ac:parameter ac:name="icon">true</ac:parameter>
              <ac:parameter ac:name="title"></ac:parameter>
              <ac:rich-text-body>
        """

        self.body.append(macro.format(admonition_type=admonition_type))

    def depart_admonition(self, node=None):
        macro = """
              </ac:rich-text-body>
            </ac:structured-macro>\n
        """
        self.body.append(macro)

    def imgtag(self, filename, suffix='\n', **attributes):
        """
        Attached image

        https://confluence.atlassian.com/display/DOC/Confluence+Storage+Format#ConfluenceStorageFormat-Images

        <ac:image>
        <ri:attachment ri:filename="atlassian_logo.gif" />
        </ac:image>

        Supported image attributes (some of these attributes mirror the equivalent HTML 4 IMG element):

        Name            Description
        ----            -----------
        ac:align        image alignment
        ac:border       Set to "true" to set a border
        ac:class        css class attribute.
        ac:title        image tool tip.
        ac:style        css style
        ac:thumbnail    Set to "true" to designate this image as a thumbnail.
        ac:alt          alt text
        ac:height       image height
        ac:width        image width

        """
        prefix = []
        atts = {}
        for (name, value) in attributes.items():
            atts[name.lower()] = value
        attlist = atts.items()
        attlist = sorted(attlist)
        parts = []
        src_part = '<ri:attachment ri:filename="%s" />' % filename
        for name, value in attlist:
            # value=None was used for boolean attributes without
            # value, but this isn't supported by XHTML.
            assert value is not None
            if isinstance(value, list):
                value = u' '.join(map(unicode, value))
            else:
                # First assume Python 2
                try:
                    value = unicode(value)
                # Otherwise, do it the Python 3 way
                except NameError:
                    value = str(value)

            parts.append('ac:%s="%s"' % (name.lower(), self.attval(value)))

        infix = '</ac:image>'
        return ''.join(prefix) + '<ac:image %s>%s%s' % (' '.join(parts), src_part, infix) + suffix

    def visit_image(self, node):
        atts = {}
        uri = node['uri']
        filename = os.path.basename(uri)
        atts['alt'] = node.get('alt', uri)
        atts['thumbnail'] = 'true'

        if 'width' in node:
            atts['width'] = node['width']

        if 'name' in node:
            atts['title'] = node['name']

        if (isinstance(node.parent, nodes.TextElement) or
            (isinstance(node.parent, nodes.reference) and
             not isinstance(node.parent.parent, nodes.TextElement))):
            # Inline context or surrounded by <a>...</a>.
            suffix = ''
        else:
            suffix = '\n'

        self.context.append('')
        self.body.append(self.imgtag(filename, suffix, **atts))

    def visit_title(self, node):
        if isinstance(node.parent, nodes.section) and not TitlesCache.has_title(self.document):
            h_level = self.section_level + self.initial_header_level - 1
            if h_level == 1:
                # Confluence take first title for page title from rst
                # It use for making internal links
                TitlesCache.set_title(self.document, node.children[0])

                # ignore first header; document must have title header
                raise nodes.SkipNode

        HTMLTranslator.visit_title(self, node)

    def visit_target(self, node):
        """
        Anchor Macro

        https://confluence.atlassian.com/display/DOC/Anchor+Macro

        <ac:structured-macro ac:name="anchor">
          <ac:parameter ac:name="">here</ac:parameter>
        </ac:structured-macro>
        """

        # Anchor confluence macros
        anchor_macros = """
            <ac:structured-macro ac:name="anchor">
              <ac:parameter ac:name="">%s</ac:parameter>
            </ac:structured-macro>
        """

        if 'refid' in node or 'refname' in node:

            if 'refuri' in node:
                link = node['refuri']
            elif 'refid' in node:
                link = node['refid']
            else:
                link = node['refname']

            self.body.append(anchor_macros % link)

    def depart_target(self, node):
        pass


    def visit_literal_block(self, node):
        """
        Code Block Macro

        https://confluence.atlassian.com/display/DOC/Code+Block+Macro

        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="title">This is my title</ac:parameter>
          <ac:parameter ac:name="theme">FadeToGrey</ac:parameter>
          <ac:parameter ac:name="linenumbers">true</ac:parameter>
          <ac:parameter ac:name="language">xml</ac:parameter>
          <ac:parameter ac:name="firstline">0001</ac:parameter>
          <ac:parameter ac:name="collapse">true</ac:parameter>
          <ac:plain-text-body><![CDATA[<b>This is my code</b>]]></ac:plain-text-body>
        </ac:structured-macro>
        """

        parts = ['<ac:structured-macro ac:name="code">']
        if 'language' in node:

            # Collapsible argument
            if node['language'] == 'collapse':
                parts.append('<ac:parameter ac:name="collapse">true</ac:parameter>')

            valid = ['actionscript3', 'bash', 'csharp', 'coldfusion', 'cpp', 'css', 'delphi', 'diff', 'erlang',
                     'groovy', 'html/xml', 'java', 'javafx', 'javascript', 'none', 'perl', 'php', 'powershell',
                     'python', 'ruby', 'scala', 'sql', 'vb']

            if node['language'] not in valid:
                node['language'] = 'none'

            parts.append('<ac:parameter ac:name="language">%s</ac:parameter>' % node['language'])

        if 'linenos' in node and node['linenos']:
            parts.append('<ac:parameter ac:name="linenumbers">true</ac:parameter>')

        if 'caption' in node and node['caption']:
            parts.append('<ac:parameter ac:name="title">%s</ac:parameter>' % node['caption'])

        parts.append('<ac:plain-text-body><![CDATA[%s]]></ac:plain-text-body>' % node.rawsource)
        parts.append('</ac:structured-macro>')

        self.body.append(''.join(parts))
        raise nodes.SkipNode

    def visit_download_reference(self, node):
        """
        Link to an attachment

        https://confluence.atlassian.com/display/DOC/Confluence+Storage+Format#ConfluenceStorageFormat-Links

        <ac:link>
          <ri:attachment ri:filename="atlassian_logo.gif" />
          <ac:plain-text-link-body><![CDATA[Link to a Confluence Attachment]]></ac:plain-text-link-body>
        </ac:link>
        """
        if 'filename' not in node:
            self.context.append('')
            return

        text = None
        if len(node.children) > 0 and len(node.children[0].children) > 0:
            text = node.children[0].children[0]

        parts = [
            '<ac:link>',
            '<ri:attachment ri:filename="%s" />' % node['filename'],
            '<ac:plain-text-link-body>',
            '<![CDATA[%s]]>' % text if text else '',
            '</ac:plain-text-link-body>',
            '</ac:link>',
        ]

        self.body.append(''.join(parts))
        raise nodes.SkipNode

    def visit_section(self, node):
        # removed section open tag
        self.section_level += 1

    def depart_section(self, node):
        # removed section close tag
        self.section_level -= 1

    def visit_reference(self, node):
        anchor_macros = """
            <ac:structured-macro ac:name="anchor">
              <ac:parameter ac:name="">%s</ac:parameter>
            </ac:structured-macro>
        """

        atts = {'class': 'reference'}
        if node.get('internal') or 'refuri' not in node:
            atts['class'] += ' internal'
        else:
            atts['class'] += ' external'
        if 'refuri' in node:
            atts['href'] = ''
            # Confluence makes internal links with prefix from page title
            if node.get('internal') and TitlesCache.has_title(self.document):
                atts['href'] += '#%s-' % TitlesCache.get_title(self.document).replace(' ', '')

            atts['href'] += node['refuri']
            if self.settings.cloak_email_addresses and atts['href'].startswith('mailto:'):
                atts['href'] = self.cloak_mailto(atts['href'])
                self.in_mailto = 1
        else:
            assert 'refid' in node, 'References must have "refuri" or "refid" attribute.'

            atts['href'] = ''
            # Confluence makes internal links with prefix from page title
            if node.get('internal') and TitlesCache.has_title(self.document):
                atts['href'] += '#%s-' % TitlesCache.get_title(self.document).replace(' ', '')
            atts['href'] += node['refid']


        if not isinstance(node.parent, nodes.TextElement):
            assert len(node) == 1 and isinstance(node[0], nodes.image)
            atts['class'] += ' image-reference'
        if 'reftitle' in node:
            atts['title'] = node['reftitle']


        if atts['href'].startswith("#"):

            href = atts['href']
            start = href.find('https:')
            href = href[start:]
            parts = href.split('/')

            if start >= 0 and len(parts) > 2 and "#" in parts[-2] and "#" in parts[-1]:
                # if it's a bitbucket viewcode
                anchor = None
                href = "/".join(parts[:-1])
                atts['href'] = href


                if 'refuri' in node:
                    uri = node.get('refuri')
                    if uri:
                        start = uri.find('/browse/') + 8
                        uri = uri[start:]
                        uri_parts = uri.split('/')
                        uri_parts[-1] = uri_parts[-1].replace('#', '')
                        uri_parts[-2] = uri_parts[-2][:uri_parts[-2].find('.py')]
                        anchor = '.'.join(uri_parts)


                elif 'reftitle' in node and node.get('reftitle'):
                    title = node.get('reftitle')
                    if title:
                        anchor = title.split('#')[-1]

                if anchor:
                    self.body.append(anchor_macros % anchor)

                self.body.append(anchor_macros % parts[-1][1:])


        if "refpage" in node and not atts['href'].startswith('http'):
            # Fix links for confluence pages
            refpage = node.get('refpage')
            target = None

            if 'refuri' in node:
                uri = node.get('refuri')
                if uri:
                    target = uri.split('/')[-1][1:]

            if 'reftitle' in node:
                if not target:
                    title = node.get('reftitle')
                    target = title.split('#')[-1]

            href = refpage.get('server_path') + "#%s-" % refpage.get('short_title')
            if target:
                href += target
            atts['href'] = href

        self.body.append(self.starttag(node, 'a', '', **atts))

        if node.get('secnumber'):
            self.body.append(('%s' + self.secnumber_suffix) % '.'.join(map(str, node['secnumber'])))


    def visit_table(self, node):
        """ Fix ugly table border
        """
        self.context.append(self.compact_p)
        self.compact_p = True
        classes = ' '.join(['docutils', self.settings.table_style]).strip()
        self.body.append(
            self.starttag(node, 'table', CLASS=classes, border="0"))

    def write_colspecs(self):
        """ Fix ugly column width
        """
        pass


class ImageConf(images.Image):
    """
    Image confluence directive
    """

    def run(self):
        # remove 'align' processing
        # remove 'target' processing

        self.options.pop('align', None)
        reference = directives.uri(self.arguments[0])
        self.options['uri'] = reference
        set_classes(self.options)
        image_node = nodes.image(self.block_text, **self.options)
        self.add_name(image_node)
        return [image_node]


class TocTree(Directive):
    """
        Replace sphinx "toctree" directive to confluence macro

        Table of Contents Macro

        https://confluence.atlassian.com/display/DOC/Table+of+Contents+Macro

        <ac:structured-macro ac:name="toc">
          <ac:parameter ac:name="style">square</ac:parameter>
          <ac:parameter ac:name="minLevel">1</ac:parameter>
          <ac:parameter ac:name="maxLevel">3</ac:parameter>
          <ac:parameter ac:name="type">list</ac:parameter>
        </ac:structured-macro>
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'maxdepth': int,
        'name': directives.unchanged,
        'caption': directives.unchanged_required,
        'glob': directives.flag,
        'hidden': directives.flag,
        'includehidden': directives.flag,
        'titlesonly': directives.flag,
    }

    def run(self):
        macro = """
            <ac:structured-macro ac:name="toc">
              <ac:parameter ac:name="style">square</ac:parameter>
              <ac:parameter ac:name="minLevel">1</ac:parameter>
              <ac:parameter ac:name="maxLevel">3</ac:parameter>
              <ac:parameter ac:name="type">list</ac:parameter>
            </ac:structured-macro>\n
        """

        attributes = {'format': 'html'}
        raw_node = nodes.raw('', macro, **attributes)
        return [raw_node]


class JiraIssuesDirective(Directive):
    """
    JIRA Issues Macro

    https://confluence.atlassian.com/doc/jira-issues-macro-139380.html

    <ac:structured-macro ac:name="jira" ac:schema-version="1" ac:macro-id="da6b6413-0b93-4052-af90-dbb252175860">
        <ac:parameter ac:name="server">Atlassian JIRA (JAC)</ac:parameter>
        <ac:parameter ac:name="columns">key,summary,created</ac:parameter>
        <ac:parameter ac:name="maximumIssues">20</ac:parameter>
        <ac:parameter ac:name="jqlQuery">project = CONF AND FixVersion=5.8 </ac:parameter>
        <ac:parameter ac:name="serverId">146780e9-1234-312f-1243-ed0555666fa</ac:parameter>
    </ac:structured-macro>
    """
    required_arguments = 1
    has_content = False
    final_argument_whitespace = True

    option_spec = {
        "anonymous": true_false,
        "server_id": directives.unchanged,
        "baseurl": directives.unchanged,
        "columns": directives.unchanged,
        "count": true_false,
        "height": directives.positive_int,
        "title": directives.unchanged,
        "render_mode": static_dynamic,
        "url": directives.unchanged,
        "width": directives.unchanged,
        "maximum_issues": directives.positive_int
    }

    def run(self):
        result = ['<ac:structured-macro ac:name="jira" ac:schema-version="1">']
        param_macro = '<ac:parameter ac:name="{name}">{value}</ac:parameter>'

        for name, value in self.options.items():
            result.append(param_macro.format(name=underscore_to_camelcase(name), value=value))

        jql_query = self.arguments[0]
        result.append(param_macro.format(name='jqlQuery', value=jql_query))

        result.append('</ac:structured-macro>')
        attributes = {'format': 'html'}

        raw_node = nodes.raw('', '\n'.join(result), **attributes)
        return [raw_node]


class JiraIssueRole(roles.GenericRole):
    def __call__(self, role, rawtext, text, *args, **kwargs):
        macro = """\
          <ac:structured-macro ac:name="jira" ac:schema-version="1">
            <ac:parameter ac:name="key">{key}</ac:parameter>
            <ac:parameter ac:name="showSummary">false</ac:parameter>
          </ac:structured-macro>
        """
        attributes = {'format': 'html'}
        return [nodes.raw('', macro.format(key=text), **attributes)], []


class JiraUserRole(roles.GenericRole):
    def __call__(self, role, rawtext, text, *args, **kwargs):
        macro = """\
        <ac:link>
            <ri:user ri:username="{username}"/>
        </ac:link>
        """
        attributes = {'format': 'html'}
        return [nodes.raw('', macro.format(username=text), **attributes)], []



class CaptionedCodeBlock(CodeBlock):

    def run(self):
        ret = super(CaptionedCodeBlock, self).run()
        caption = self.options.get('caption')
        if caption and isinstance(ret[0], nodes.container):
            container_node = ret[0]
            if isinstance(container_node[0], nodes.caption):
                container_node[1]['caption'] = caption
                return [container_node[1]]
        return ret


class EmoteDirective(Directive):
    required_arguments = 1
    def run(self):
        macro = """<ac:emoticon ac:name="{name}" />"""
        attributes = {'format': 'html'}
        name = self.arguments[0]
        raw_node = nodes.raw('', macro.format(name=name), **attributes)
        return [raw_node]

def underscore_to_camelcase(text):
    return ''.join(word.title() if i else word for i, word in enumerate(text.split('_')))


def get_path():
    from os import path
    package_dir = path.abspath(path.dirname(__file__))
    template_path = path.join(package_dir, 'themes')
    return template_path


def find_page(pages, **params):
    for page in pages:
        if all(page.get(param) == value for param, value in params.items()):
            return page
    else:
        return None



def fix_references(app, doctree, docname):
    pages = app.config.sphinx_confluence_pages
    for page in pages:
        if page.get('local_path').endswith(docname):
            break
    else:
        logger.debug('Didn\'t find confluence page for %s', docname)
        return

    for node in doctree.traverse():
        if hasattr(node, 'tagname') and node.tagname == 'reference':
            if "refuri" in node:
                uri = node.get('refuri')
                if not uri.startswith('..') or 'http' in uri:
                    continue

                parts = uri.split('/')
                if len(parts) < 2:
                    continue
                uri = '/'.join(part for part in parts if not part.startswith('#'))
                docpath = os.path.abspath(os.path.join(page.get('local_path'), uri))
                realpage = find_page(pages, local_path=docpath)
                if realpage:
                    logger.debug('Confluence page \'%s\' found for reference node with uri %s', realpage.get('title'), uri)
                    node['refpage'] = realpage


def publish_main(app, exception):
    if exception is not None:
        return

    if app.config.sphinx_confluence_publish is False:
        return
    try:
        from conf_publisher.publish import DEFAULT_CONFLUENCE_API_VERSION, create_publisher, create_confluence_api, parse_authentication, ConfigLoader
    except ImportError:
        raise ImportError("Could not import from conf_publisher. Is confluence-publisher installed?")

    publish_options = app.config.sphinx_confluence_publish_options
    auth_options = publish_options.pop('auth')
    auth = parse_authentication(**auth_options)
    config = ConfigLoader.from_yaml(app.config.sphinx_confluence_config_path)

    confluence_api = create_confluence_api(DEFAULT_CONFLUENCE_API_VERSION, config.url, auth)
    publisher = create_publisher(config, confluence_api)
    print('Publishing...')
    publisher.publish(**publish_options)


def setup(app):
    """
    :type app: sphinx.application.Sphinx
    """
    watermark_default = 'This documentation was generated automatically. Do not edit directly, changes will be overwritten'
    app.add_config_value('sphinx_confluence_pages', list(), False)
    app.add_config_value('sphinx_confluence_publish', False, False)
    app.add_config_value('sphinx_confluence_config_path', 'config.yml', False)
    app.add_config_value('sphinx_confluence_publish_options', dict(), False)


    app.config.html_theme_path = [get_path()]
    app.config.html_theme = 'confluence'
    app.config.html_scaled_image_link = False
    if LooseVersion(sphinx.__version__) >= LooseVersion("1.4"):
        app.set_translator("html", HTMLConfluenceTranslator)
        app.set_translator("json", HTMLConfluenceTranslator)
    else:
        app.config.html_translator_class = 'sphinx_confluence.HTMLConfluenceTranslator'
    app.config.html_add_permalinks = ''

    jira_issue = JiraIssueRole('jira_issue', nodes.Inline)
    app.add_role(jira_issue.name, jira_issue)

    jira_user = JiraUserRole('jira_user', nodes.Inline)
    app.add_role(jira_user.name, jira_user)

    app.add_directive('image', ImageConf)
    app.add_directive('toctree', TocTree)
    app.add_directive('jira_issues', JiraIssuesDirective)
    app.add_directive('code-block', CaptionedCodeBlock)
    app.add_directive('emote', EmoteDirective)
    app.connect('doctree-resolved', fix_references)
    app.connect('build-finished', publish_main)


    app.add_builder(JSONConfluenceBuilder)

if __name__ == '__main__':
    publish_main()
