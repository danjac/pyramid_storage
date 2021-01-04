pyramid_storage
===============

**pyramid_storage** is a simple file upload manager for the `Pyramid`_ framework. It currently supports uploads to the local file system and to the Amazon S3 cloud storage service.


Installation
-------------

Install with **pip install pyramid_storage**. To install from source, unzip/tar, cd and **python setup.py install**.

Bugs and issues
---------------

Please report bugs and issues (and better still, pull requests) on the `Github`_ repo.

Getting started
---------------

There are a number of ways to configure **pyramid_storage** with your Pyramid app.

The easiest way is to add **pyramid_storage** to the **pyramid.includes** directive in your configuration file(s)::

    pyramid.includes =
        pyramid_storage


Alternatively you can use :meth:`pyramid.config.Configurator.include` in your app setup::

    config.include('pyramid_storage')


Either setup will add an instance of :class:`pyramid_storage.storage.FileStorage` to your app registry. The instance
will also be available as a property of your request as **request.storage**.

To use S3 file storage instead of storing files locally on your server (the default assumption)::

    pyramid.includes =
        pyramid_storage.s3

alternatively::

    config.include('pyramid_storage.s3')

If you are configuring a pyramid async setup and require all drivers to be async aware, use::

    pyramid.includes =
        pyramid_storage.s3_async

or::

    config.include('pyramid_storage.s3_async')

Configuration
-------------

**Local file storage (default)**

The available settings are listed below:

==============         =================      ==================================================================
Setting                Default                Description
==============         =================      ==================================================================
**base_path**          **required**           Absolute location for storing uploads
**base_url**                                  Relative or absolute base URL for uploads; must end in slash ("/")
**extensions**         ``default``            List of extensions or extension groups (see below)
**name**               ``storage``            Name of property added to request, e.g. **request.storage**
==============         =================      ==================================================================

**S3 file storage**

===================    =================      ==================================================================
Setting                Default                Description
===================    =================      ==================================================================
**aws.access_key**     **required**           AWS access key
**aws.secret_key**     **required**           AWS secret key
**aws.bucket_name**    **required**           AWS bucket
**aws.acl**            ``public-read``        `AWS ACL permissions <https://github.com/boto/boto/blob/v2.13.2/boto/s3/acl.py#L25-L28>`_
**base_url**                                  Relative or absolute base URL for uploads; must end in slash ("/")
**extensions**         ``default``            List of extensions or extension groups (see below)
**name**               ``storage``            Name of property added to request, e.g. **request.storage**

**use_path_style**     ``False``              Use paths for buckets instead of subdomains (useful for testing)
**is_secure**          ``True``               Use ``https``
**host**               ``None``               Host for Amazon S3 server (eg. `localhost`)
**port**               ``None``               Port for Amazon S3 server (eg. `5000`)
**region**             ``None``               Region identifier, *host* and *port* will be ignored
**num_retries**        ``1``                  Number of retry for connection errors
**timeout**            ``5``                  HTTP socket timeout in seconds
===================    =================      ==================================================================

**S3 Async file storage**

===================    =================      ==================================================================
Setting                Default                Description
===================    =================      ==================================================================
**aws.access_key**     **required**           AWS access key
**aws.secret_key**     **required**           AWS secret key
**aws.bucket_name**    **required**           AWS bucket
**aws.acl**            ``public-read``        `AWS ACL permissions <https://github.com/boto/boto/blob/v2.13.2/boto/s3/acl.py#L25-L28>`_
**base_url**                                  Relative or absolute base URL for uploads; must end in slash ("/")
**extensions**         ``default``            List of extensions or extension groups (see below)
**name**               ``storage``            Name of property added to request, e.g. **request.storage**

**use_path_style**     ``False``              Use paths for buckets instead of subdomains (useful for testing)
**is_secure**          ``True``               Use ``https`` when a Host is defined
**host**               ``None``               Host for Amazon S3 server (eg. `localhost`)
**port**               ``None``               Port for Amazon S3 server (eg. `5000`)
**region**             ``None``               Region identifier, *is_secure*, *host* and *port* will be ignored
**num_retries**        ``5``                  Number of retry for connection errors
**timeout**            ``5``                  HTTP socket connection timeout in seconds
**read_timeout**       ``10``                 Timeout when reading from the HTTP socket in seconds
**keepalive_timeout**  ``12``                 Number of seconds before closing the aiohttp Keep-Alive connection
===================    =================      ==================================================================

**Google Cloud file storage**

======================    =================      ==================================================================
Setting                   Default                Description
======================    =================      ==================================================================
**gcloud.credentials**    **required**           Path to the Service Accounts credentials JSON file.
**gcloud.bucket_name**    **required**           Google Cloud bucket
**gcloud.acl**            ``publicRead``         `Google Cloud ACL permissions <https://cloud.google.com/storage/docs/access-control/making-data-public>`_
**base_url**                                     Relative or absolute base URL for uploads; must end in slash ("/")
**extensions**            ``default``            List of extensions or extension groups (see below)
**name**                  ``storage``            Name of property added to request, e.g. **request.storage**
=====================     =================      ==================================================================


**Configuring extensions:** extensions are given as a list of space-separated extensions or groups of extensions. These groups provide a convenient
shortcut for including a large number of extensions. Each group must be separated by a plus-sign "+". Some examples:

- **storage.extensions = images** - all image formats e.g. ``jpg``, ``gif``, ``png``
- **storage.extensions = images+documents** - image and document formats (``rtf``, ``doc`` etc)
- **storage.extensions = images+documents+rst xml json** - all image and document formats, plus the extensions ``rst``, ``xml`` and ``json``.


The extension groups are listed below:

============    ==========================================
Group           Extensions
============    ==========================================
any             **all** extensions (including no extensions)
text            txt
documents       pdf rtf odf ods gnumeric abw doc docx xls xlsx
images          jpg jpe jpeg png gif svg bmp tiff
audio           wav mp3 aac ogg oga flac
video           mpeg 3gp avi divx dvr flv mp4 wmv
data            csv ini json plist xml yaml yml
scripts         js php pl py rb sh
archives        gz bz2 zip tar tgz txz 7z
executables     so exe dll
default         documents+images+text+data
============    ==========================================


Usage: local file storage
-------------------------

.. warning::
    It is the responsibility of the deployment team to ensure that target directories used in file uploads have the appropriate read/write permissions.


When uploading a file in a view, call :meth:`pyramid_storage.storage.FileStorage.save` to save the file to your file system::

    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPSeeOther

    @view_config(route_name='upload',
                 request_method='POST')
    def upload(request):
        request.storage.save(request.POST['my_file'])
        return HTTPSeeOther(request.route_url('home'))


This operation will save the file to your file system under the top directory specified by the **base_path** setting.

If the file does not have the correct file extension, a :class:`pyramid_storage.exceptions.FileNotAllowed` exception is raised. A more secure way of writing the above would be::

    from pyramid_storage.exceptions import FileNotAllowed

    @view_config(route_name='upload',
                 request_method='POST')
    def upload(request):
        try:
            request.storage.save(request.POST['my_file'])
        except FileNotAllowed:
            request.session.flash('Sorry, this file is not allowed')
        return HTTPSeeOther(request.route_url('home'))


You can override the default extensions in the method call::

    from pyramid_storage.exceptions import FileNotAllowed

    @view_config(route_name='upload',
                 request_method='POST')
    def upload(request):
        try:
            request.storage.save(request.POST['my_file'],
                                 extensions=('jpg', 'png', 'txt'))
        except FileNotAllowed:
            request.session.flash('Sorry, this file is not allowed')
        return HTTPSeeOther(request.route_url('home'))


You may also wish to obfuscate or randomize the filename. The ``randomize`` argument will generate a random filename, preserving the extension::

    filename = request.storage.save(request.POST['my_file'], randomize=True)

So for example if your filename is ``test.jpg`` the new filename will be something like ``235a344c-8d70-498a-af0a-151afdfcd803.jpg``.

If there is a filename clash (i.e. another file with the same name is in the target directory) a numerical suffix is added to the new filename. For example,
if you have an existing file ``test.jpg`` then the next file with that name will be renamed ``test-1.jpg`` and so on.

.. warning::
    Remember to ensure your forms include the attribute **enctype="multipart/form-data"** or your uploaded files will be empty.

If you pass in the ``folder`` argument this will be used to add subfolder(s)::

    request.storage.save(request.POST['my_file'], folder="photos")

The above call will store the contents of ``my_file`` under the directory ``photos`` under your base path.

If you want to check in advance that the extension is permitted (for example, in the form validation stage) you can use :meth:`pyramid_storage.storage.FileStorage.file_allowed`::

    request.storage.file_allowed(request.POST['my_file'])

To access the URL of the file, for example in your Python code or templates, use the :meth:`pyramid_storage.storage.FileStorage.url` method::

    request.storage.url(filename)

You may not wish to provide public access to files - for example users may upload to private directories. In that case you can simply serve the file in your views::

    from pyramid.response import FileResponse

    @view_config(route_name='download')
    def download(request):
        filename = request.params['filename']
        return FileResponse(request.storage.path(filename))

Usage: s3 file storage
----------------------

.. warning::
    S3 support requires you install the `Boto`_ library separately (e.g. ``pip install boto``).

    Alternatively you can install **pyramid_storage** with the mandatory extra dependencies: ``pip install pyramid_storage[s3]``

.. warning::
    It is the responsibility of the deployment team to ensure that the application has the correct AWS settings and permissions.

Basic usage is similar to **LocalFileStorage**::

    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPSeeOther

    @view_config(route_name='upload',
                 request_method='POST')
    def upload(request):
        request.storage.save(request.POST['my_file'])
        return HTTPSeeOther(request.route_url('home'))


One difference is that filenames are not resolved with a numeric suffix as with local files, to prevent network round-trips. Instead you can pass the ``replace`` argument to replace the file (default is **False**)::


    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPSeeOther

    @view_config(route_name='upload',
                 request_method='POST')
    def upload(request):
        request.storage.save(request.POST['my_file'], replace=True)
        return HTTPSeeOther(request.route_url('home'))

Alternatively you can use the ``randomize`` argument to ensure a (near) unique filename.

The  ``storage.base_url`` setting should be set to ``//s3amazonaws.com/<my-bucket-name>/`` unless you want to serve the file behind a proxy or through your Pyramid application.

Usage: s3 async file storage
----------------------

.. warning::
    S3 support requires you install the `aioboto3`_ and `aiofile`_ library separately (e.g. ``pip install aioboto3 aiofile``).

    Alternatively you can install **pyramid_storage** with the mandatory extra dependencies: ``pip install pyramid_storage[s3_async]``

.. warning::
    It is the responsibility of the deployment team to ensure that the application has the correct AWS settings and permissions.

Basic usage is similar to **S3FileStorage**, but every file operation must be await'ed::

    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPSeeOther

    @view_config(route_name='upload',
                 request_method='POST')
    async def upload(request):
        await request.storage.save(request.POST['my_file'])
        return HTTPSeeOther(request.route_url('home'))

Usage: Google Cloud Storage
---------------------------

.. warning::
    Google Cloud Storage support requires you to install the `google-cloud-storage`_ library separately (e.g. ``pip install google-cloud-storage``).

    Alternatively you can install **pyramid_storage** with the mandatory extra dependencies: ``pip install pyramid_storage[gcloud]``

.. warning::
    It is the responsibility of the deployment team to ensure that the application has the correct settings and permissions.

Basic usage is similar to **LocalFileStorage**::

    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPSeeOther

    @view_config(route_name='upload',
                 request_method='POST')
    def upload(request):
        request.storage.save(request.POST['my_file'])
        return HTTPSeeOther(request.route_url('home'))


One difference is that filenames are not resolved with a numeric suffix as with local files, to prevent network round-trips.
Instead you can pass the ``replace`` argument to replace the file (default is **False**)::


    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPSeeOther

    @view_config(route_name='upload',
                 request_method='POST')
    def upload(request):
        request.storage.save(request.POST['my_file'], replace=True)
        return HTTPSeeOther(request.route_url('home'))

Alternatively you can use the ``randomize`` argument to ensure a (near) unique filename.

The  ``storage.base_url`` setting should be set to ``//storage.googleapis.com/<my-bucket-name>/`` unless you want to serve the file behind a CDN or through your Pyramid application.

Testing
-------

It's easier to run unit tests on your upload views without actually handling real files. The class :class:`pyramid_storage.storage.DummyFileStorage` provides a convenient way to mock these operations.

This class stores the names of the files internally for your assertions in the **saved** attribute::

    import mock

    from pyramid.testing import DummyRequest
    from pyramid_storage.storage import DummyFileStorage

    def test_my_upload():
        from .views import my_upload_view
        req = DummyRequest()
        req.storage = DummyFileStorage()

        my_file = mock.Mock()
        my_file.filename = 'test.jpg'

        req.POST['my_file'] = my_file

        res = my_upload_view(req)
        assert 'test.jpg' in req.storage.saved


Not that *DummyFileStorage* only provides one or two convenience methods. You may wish to extend this class for your own specific needs.


API
---

.. module:: pyramid_storage.exceptions

.. autoclass:: FileNotAllowed

.. module:: pyramid_storage.local

.. autoclass:: LocalFileStorage
   :members:

.. module:: pyramid_storage.s3

.. autoclass:: S3FileStorage
   :members:

.. autoclass:: S3AsyncFileStorage
   :members:

.. module:: pyramid_storage.gcloud

.. autoclass:: GoogleCloudStorage
   :members:

.. module:: pyramid_storage.testing

.. autoclass:: DummyFileStorage
   :members:

.. _Boto: http://pypi.python.org/pypi/boto/
.. _Pyramid: http://pypi.python.org/pypi/pyramid/
.. _Github: https://github.com/danjac/pyramid_storage
.. _google-cloud-storage: https://github.com/googleapis/google-cloud-python
