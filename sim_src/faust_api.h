#ifndef FAUST_API_H
#define FAUST_API_H

#ifdef __cplusplus
extern "C" {
#endif

/* Opaque handle */
typedef void* faust_handle_t;

/* Lifecycle */
faust_handle_t faust_create(void);
void           faust_destroy(faust_handle_t h);
void           faust_init(faust_handle_t h, int sample_rate);

/* DSP info */
int  faust_get_num_inputs(faust_handle_t h);
int  faust_get_num_outputs(faust_handle_t h);

/* Parameter access */
int         faust_get_params_count(faust_handle_t h);
const char* faust_get_param_address(faust_handle_t h, int index);
void        faust_set_param(faust_handle_t h, const char* path, float value);
float       faust_get_param(faust_handle_t h, const char* path);

/* Audio processing */
void faust_compute(faust_handle_t h, int count,
                   float** inputs, float** outputs);

/* OLED frame buffer (SSD1306: 128x64, 1bpp, 8 pages x 128 cols) */
#define OLED_WIDTH    128
#define OLED_HEIGHT   64
#define OLED_BUF_SIZE (OLED_WIDTH * OLED_HEIGHT / 8)

const unsigned char* faust_oled_get_framebuf(faust_handle_t h);
void faust_oled_clear(faust_handle_t h);
void faust_oled_set_pixel(faust_handle_t h, int x, int y, int on);
void faust_oled_draw_text(faust_handle_t h, int x, int y,
                          const char* text, int font_size);
void faust_oled_update(faust_handle_t h);

#ifdef __cplusplus
}
#endif
#endif /* FAUST_API_H */
