# coding: utf-8

import email
import lxml
from django.template import Template, Context
from django.template.loader import render_to_string
import u2u_decode
from lib import decode

class EmailAddress(object):
    def __init__(self, address):
        self.fulladdress = u2u_decode.u2u_decode(address).strip("\r\t\n")
        (self.name, self.address) = email.utils.parseaddr(self.fulladdress)
        if self.name == "":
            self.fulladdress = self.address
        
    def __str__(self):
        return self.fulladdress

class Email(object):
    def __init__(self, msg, mformat="plain", dformat="plain", links="0"):
        self.attached_map = {}
        self.contents = {"html" : "", "plain" : ""}
        self.headers = []
        self.attachments = {}
        self.mformat = mformat
        self.dformat = dformat
        self.links = links

        self.__parse(msg)

        if not self.contents.has_key(mformat) or self.contents[mformat] == "":
            # Fallback
            self.mformat = mformat == "html" and "plain" or "html"

        self.body = \
            getattr(self, "viewmail_%s" % self.mformat) \
            (self.contents[self.mformat], links=links)

    def __parse_default(self, msg, level):
        """Default parser

        All parts handled by this parser will be consireded as
        attachments.
        """
        fname = msg.get_filename()
        if fname is not None:
            decoded = decode_header(fname)
            value = decoded[0][1] is None and decoded[0][0] \
                or unicode(decoded[0][0], decoded[0][1])
        else:
            value = "part_%s" % level
        self.attachments[level] = value

    def _parse_text(self, msg, level):
        """Displayable content parser

        text, html, calendar, etc. All those contents can be displayed
        inside a navigator.
        """
        if msg.get_content_subtype() not in ["plain", "html"]:
            self.__parse_default(msg, level)
            target = "plain"
        else:
            target = msg.get_content_subtype()
        self.contents[target] += decode(msg.get_payload(decode=True), 
                                        charset=msg.get_content_charset())

    def _parse_image(self, msg, level):
        """image/* parser

        The only reason to make a specific parser for images is that,
        sometimes, messages embark inline images, which means they
        must be displayed and not attached.
        """
        if self.dformat == "html" and self.links != "0" \
                and msg.has_key("Content-Disposition"):
            if msg["Content-Disposition"].startswith("inline"):
                cid = None
                if msg.has_key("Content-ID"):
                    m = re.match("<(.+)>", msg["Content-ID"])
                    cid = m is not None and m.group(1) or msg["Content-ID"]
                fname = msg.get_filename()
                if fname is None:
                    if msg.has_key("Content-Location"):
                        fname = msg["Content-Location"]
                    elif cid is not None:
                        fname = cid
                    else:
                        # I give up for now :p
                        return
                self.attached_map[cid] = re.match("^http:", fname) and fname \
                    or self.__save_image(fname, msg)
                return
        self.__parse_default(msg, level)  

    def __parse(self, msg, level=None):
        """Recursive email parser

        A message structure can be complex. To correctly handle
        unknown MIME types, a simple rule is applied : if I don't know
        how to display a specific part, it becomes an attachment! If
        no name is specified for an attachment, the part number
        described in the RFC 3501 (which retrieves BODY sections) is
        used to build a file name (like part_1.1).

        :param msg: message (or part) to parse
        :param level: current part number
        """
        if msg.is_multipart() and msg.get_content_maintype() != "message":
            cpt = 1
            for part in msg.get_payload():
                nlevel = level is None and ("%d" % cpt) \
                    or "%s.%d" % (level, cpt)
                self.__parse(part, nlevel)
                cpt += 1
            return

        if level is None: 
            level = "1"
        try:
            getattr(self, "_parse_%s" % msg.get_content_maintype())(msg, level)
        except AttributeError:
            self.__parse_default(msg, level)

    def __save_image(self, fname, part):
        """Save an inline image on the filesystem.

        Some HTML messages are using inline images (attached images
        with links on them inside the body). In order to display them,
        images are saved on the filesystem and links contained in the
        message are modified.

        :param fname: the image associated filename
        :param part: the email part that contains the image payload
        """
        if re.search("\.\.", fname):
            return None
        path = "/static/tmp/" + fname
        fp = open(settings.MODOBOA_DIR + path, "wb")
        fp.write(part.get_payload(decode=True))
        fp.close()
        return path

    def map_cid(self, url):
        import re

        m = re.match(".*cid:(.+)", url)
        if m:
            if self.attached_map.has_key(m.group(1)):
                return self.attached_map[m.group(1)]
        return url

    def render_headers(self, **kwargs):
        return render_to_string("common/mailheaders.html", {
                "headers" : self.headers,
                })
        
    def viewmail_plain(self, content, **kwargs):
        return "<pre>%s</pre>" % content

    def viewmail_html(self, content, **kwargs):
        if content is None or content == "":
            return (False, "")
        links = kwargs.has_key("links") and kwargs["links"] or "0"
        html = lxml.html.fromstring(content) 
        if links == "0":
            html.rewrite_links(lambda x: None)
        else:
            html.rewrite_links(self.map_cid)
        body = html.find("body")
        if body is None:
            body = lxml.html.tostring(html)
        else:
            body = lxml.html.tostring(body)
            body = re.sub("<(/?)body", lambda m: "<%sdiv" % m.group(1), body)
        body = Template(body).render(Context({}))
        return body
