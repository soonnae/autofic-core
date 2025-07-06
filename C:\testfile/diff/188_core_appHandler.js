module.exports.redirect = function (req, res) {
       const allowedUrls = ['https://example.com', 'https://another-trusted-site.com'];
       const redirectUrl = req.query.url;

       if (redirectUrl && allowedUrls.includes(redirectUrl)) {
           res.redirect(redirectUrl);
       } else {
           res.send('Invalid or untrusted redirect URL');
       }
   }

