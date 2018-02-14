# sphinx-confluence

A sphinx plugin for building and publishing sphinx documentation to Atlassian Confluence Server.

## This Fork

This fork makes some notable changes from its [upstream counterpart](https://github.com/Arello-Mobile/sphinx-confluence):

- Supports cross-references between documents (requires confluence-publisher)
- Supplies a viewcode extension compatible with Bitbucket Server (not Cloud)
- Is designed to use the style of the popular [sphinx Read The Docs theme](https://github.com/rtfd/sphinx_rtd_theme) (and supplies an accompanying CSS file to put in your Confluence space)
- Automatic publishing on a successful build is supported (use `sphinx_confluence_publish = True`, requires confluence-publisher)
- Supplies additional directives for confluence macros

To support some of these features, the [confluence-publisher](https://github.com/Arello-Mobile/confluence-publisher) project is utilized directly. Therefore, you must install and configure this package as well to use features as documented.


This has been successfully used with Confluence Server 6.2+ (tested up to 6.7) and Bitbucket Server 5.2 -- Other versions will probably work fine, but are untested.


## How use it


### Install from github.

```
pip install git+https://github.com/spyoungtech/sphinx-confluence.git
```

Note: to use publishing features you should install [confluence-publisher](https://github.com/Arello-Mobile/confluence-publisher) from github, not PyPI

```
$ pip install git+https://github.com/Arello-Mobile/confluence-publisher.git
```

Currently, the confluence-publisher code is not included in this repo and there is no companion fork at this time. Updates to this upstream repository may break compatibility with this code. If this happens and you notice it before us, please submit an issue.

### Configuration

First of all, after installation, you must enable this plugin in your [build configuration file](http://www.sphinx-doc.org/en/stable/config.html#confval-extensions)

`conf.py` by adding `sphinx_confluence` into `extensions` list. This should look something like:

```
...
extensions = ['sphinx_confluence',
              'sphinx_confluence.ext.viewcode' # viewcode for bitbucket server
              ]
sphinx_confluence_repo_path = 'https://bitbucket.company.com/projects/KEY/repositories/my-repository/browse/' # if you want viewcode
html_theme = 'sphinx_rtd_theme' # if you want to use the theme
...
```

Read The Docs style

If you want to use the rtd theme in your space (recommended) you should add the `confluence_stylesheet.css` to your space's stylesheet.


### Cross-references

If you want to support multi-page cross-references, add the following code to your conf.py

```python
from sphinx_confluence import setup_config
sphinx_confluence_pages = setup_config(config_path='/path/to/config.yml', user='myusername')
```

For now, you will be prompted for your confluence password each time you build your documentation. In the future, a way to store this information statically may be implemented if there's a strong interest for it.

The best way to use arbitrary cross-references is using [reference labels](http://www.sphinx-doc.org/en/stable/markup/inline.html#cross-referencing-arbitrary-locations). Other references should also 'just work'.

```
.. _my-reference-label:

Section to cross-reference
--------------------------

This is the text of the section.

It refers to the section itself, see :ref:`my-reference-label`.
```

### Building

The best way to build documentation is to use sphinx-quickstart and the sphinx build `make` commands. Using the `json` builder seems to work best, but the `html` builder is also supported. It's also recommended you use the `clean` option each time.

```
make clean json
```
You can also use the legacy way of building with the JSON builder (Which is deprecated and may be removed in a future release)

```
python -m sphinx -b json_conf /path/to/docroot /path/to/build/location
```

### Automatic\* publishing on successful build


If you want to publish when a *successful* build completes you can add the following config values

```python
sphinx_confluence_publish = True
sphinx_confluence_publish_options = {'auth': {'user': 'myusername'}}
```

`sphinx_confluence_publish_options` supports all the same options available through the confluence publisher commandline. The `'auth'` key is used for authentication options. 


\* you will be prompted for a password at publish time, even if you already supplied the password to build the docs.

### Dependencies

Multi-page support and publishing requires that you have [confluence-publisher](https://github.com/Arello-Mobile/confluence-publisher)  installed and a valid `config.yml`.



## ViewCode Example

The following is a sample confluence page created with this package. ([Sample .rst content](https://raw.githubusercontent.com/brandon-rhodes/sphinx-tutorial/master/handout/api.rst) from Brandon Rhodes [sphinx-tutorial](https://github.com/brandon-rhodes/sphinx-tutorial). Thanks Brandon!)

![Sample Page](https://i.imgur.com/7PkZz0k.png)

This utilizes the viewcode extension configured with a bitbucket server repository, the `[source]` link should take you right to the line where it's defined.

![Bitbucket Viewcode](https://i.imgur.com/TAXEcMY.png)


## Macros

### Emoticons

Emoticons can be added with the `emote` directive. Use the name of the emoticon and the markup will produce the emoticon 
in confluence storage format. You can find some of the names [here](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html) 
A nice way to do this is using substitutions. Here are some brief examples...

In the future we hope to provide a way to do this without needing to provide the directive substitutions yourself.

```
A table of emotes:

===============   =========
Name              symbol
===============   =========
smile             |smile|
sad               |sad|
cheeky            |cheeky|
laugh             |laugh|
wink              |wink|
thumbs-up         |thumbs-up|
thumbs-down       |thumbs-down|
information       |information|
tick              |tick|
cross             |cross|
warning           |warning|
question          |question|

===============   =========

.. |smile| emote:: smile
.. |sad| emote:: sad
.. |cheeky| emote:: cheeky
.. |laugh| emote:: laugh
.. |wink| emote:: wink
.. |thumbs-up| emote:: thumbs-up
.. |thumbs-down| emote:: thumbs-down
.. |information| emote:: information
.. |tick| emote:: tick
.. |cross| emote:: cross
.. |warning| emote:: warning
.. |question| emote:: question

```

## Known issues and Limitations

Some known limitations for the moment are:

- Requires that document filenames are unique.
- The Viewcode extension will only work on `https` bitbucket-server repositories.
- Only the standard confluence codeblock theme is supported. Some other themes wind up looking... odd.
- Connecting to the Confluence API is necessary for every build in order for cross-references to work. In the future, updates to the `config.yml` through augmenting `conf_page_maker` may eliminate this need (so long as the page location does not change)
- Overall, the viewcode implementation is fragile.

Please open an issue if you have any problems using this package or want to see improvements.
