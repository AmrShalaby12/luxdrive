(function($) {
    $(document).ready(function() {
        // إضافة تأثيرات للفلترات المتعددة
        $('.multi-select-filter .multi-select-option').click(function(e) {
            e.preventDefault();
            var link = $(this).find('a');
            if (link.length) {
                window.location.href = link.attr('href');
            }
        });
    });
})(django.jQuery);