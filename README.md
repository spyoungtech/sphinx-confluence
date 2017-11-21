## This Fork

This fork combines the [upstream project](https://github.com/Arello-Mobile/sphinx-confluence) along with the functionality of the complement [confluence-publisher](https://github.com/Arello-Mobile/confluence-publisher) project. This fork also makes some notable changes:

- Automatic publishing on a successful build is supported (use `sphinx_confluence_publish = True`)
- Is designed to use the style of the popular readthedocs theme (and supplies an accompanying CSS file to put in your Confluence space)
- Supports cross-references between documents
- Supplies a viewcode extension compatible with Bitbucket Server (not Cloud)


Sample confluence page

![Sample Page](https://i.imgur.com/2BeawdD.png)

If you have the viewcode extension configured with a bitbucket server repository, the `[source]` link should take you right to the line where it's defined.

![Bitbucket Viewcode](https://i.imgur.com/TAXEcMY.png)

Note: to use publishing features you should install confluence-publisher from github, not PyPI

```
$ pip install git+https://github.com/Arello-Mobile/confluence-publisher.git
```

Currently, the confluence-publisher code is not included in this repo and there is no companion fork, either, since no modifications to that code have been necessary. Updates to this upstream repository may break compatibility with this code. If this happens, please submit an issue.

This has been successfully used with Confluence 6.2 and Bitbucket Server 5.2 -- Other versions will probably work fine, but are untested.

## Known issues and Limitations

Some known limitations for the moment are:

- Module reference anchors do not work; links will take you to an appropriate page, but not to the location on the page.
- Will probably only work if your documentation is in the root of the repository.
- Requires that document names are unique.
- The Viewcode extension will only work on `https` bitbucket-server repositories. Depends on `/browse/` being in the URL.
- Only the standard confluence codeblock theme is supported. Some other themes wind up looking... odd.
- Connecting to the Confluence API is necessary for every build in order for cross-references to work. In the future, updates to the `config.yml` through augmenting `conf_page_maker` may eliminate this need (so long as the page location does not change)
- Uses `inspect` to get code line numbers. This can be slow/problematic for very large projects.
- Overall, implemented with hacks and, for now, is fairly fragile.

## How use it


Install from github.

```
pip install git+https://github.com/spyoungtech/sphinx-confluence.git
```

First of all, after installation, you must enable this plugin in your [build configuration file](http://www.sphinx-doc.org/en/stable/config.html#confval-extensions)
`conf.py` by adding `sphinx_confluence` into `extensions` list. This should looks like a:
```
...
extensions = ['sphinx_confluence',
              'sphinx_confluence.ext.viewcode' # viewcode for bitbucket server
              ]
sphinx_confluence_repo_path = 'https://bitbucket.company.com/projects/KEY/repositories/my-repository/browse/' # if you want viewcode
html_theme = 'sphinx_rtd_theme' # if you want to use the theme
...
```

If you want to use the rtd theme in your space (recommended) you should add the `confluence_stylesheet.css` to your space's stylesheet.

If you want to support multi-page cross-references, add the following code to your conf.py

```python
from sphinx_confluence import setup_config
sphinx_confluence_pages = setup_config(config_path='/path/to/config.yml', user='myusername')
```

If you want to publish when the build completes you can add the following config values

```python
sphinx_confluence_publish = True
sphinx_confluence_publish_options = {'auth': {'user': 'myusername'}}
```


Multi-page support and publishing requires that you have [confluence-publisher](https://github.com/Arello-Mobile/confluence-publisher)  installed and a valid `config.yml`.



