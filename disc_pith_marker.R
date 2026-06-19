#18.06.26 15:41 NZST
setwd(dirname(rstudioapi::getSourceEditorContext()$path))
library(shiny)
library(magick)

INPUT_DIR <- "."
CROP <- 0.30
files <- list.files(INPUT_DIR, pattern = "\\.tif$", ignore.case = TRUE)

imgs <- lapply(files, function(f) {
  im <- image_read(file.path(INPUT_DIR, f))
  info <- image_info(im); W <- info$width; H <- info$height
  x0 <- round(CROP * W); y0 <- round(CROP * H); cw <- W - 2 * x0; ch <- H - 2 * y0
  cr <- image_crop(im, sprintf("%dx%d+%d+%d", cw, ch, x0, y0))
  list(ras = as.raster(image_scale(cr, "1200")), W = W, H = H, x0 = x0, y0 = y0, cw = cw, ch = ch)
})
names(imgs) <- files

ui <- fluidPage(
  tags$script(HTML("$(document).on('keydown', function(e){ if(e.key==='Enter'){ $('#nxt').click(); } });")),
  titlePanel("Disc pith marker"),
  sidebarLayout(
    sidebarPanel(
      width = 3,
      selectInput("file", "Disc", choices = files),
      actionButton("prev", "Prev"), actionButton("nxt", "Next"),
      hr(),
      actionButton("flip", "Flip 180"),
      actionButton("bad", "Flag bad"),
      hr(),
      actionButton("save", "Save CSV"),
      hr(),
      verbatimTextOutput("status")
    ),
    mainPanel(
      width = 9,
      plotOutput("plot", click = "plot_click", height = "800px")
    )
  )
)

server <- function(input, output, session) {
  rec <- reactiveVal(data.frame(file = files, pith_x = NA_real_, pith_y = NA_real_,
                                flip = 0L, bad = 0L, stringsAsFactors = FALSE))
  idx <- reactiveVal(1)
  
  observeEvent(input$file, idx(match(input$file, files)))
  observeEvent(input$prev, { idx(max(1, idx() - 1)); updateSelectInput(session, "file", selected = files[idx()]) })
  observeEvent(input$nxt,  { idx(min(length(files), idx() + 1)); updateSelectInput(session, "file", selected = files[idx()]) })
  
  observeEvent(input$plot_click, {
    d <- rec(); i <- idx()
    d$pith_x[i] <- input$plot_click$x
    d$pith_y[i] <- input$plot_click$y
    rec(d)
  })
  
  observeEvent(input$flip, {
    d <- rec(); i <- idx(); im <- imgs[[files[i]]]
    d$flip[i] <- 1L - d$flip[i]
    if (!is.na(d$pith_x[i])) { d$pith_x[i] <- im$W - d$pith_x[i]; d$pith_y[i] <- im$H - d$pith_y[i] }
    rec(d)
  })
  
  observeEvent(input$bad, { d <- rec(); i <- idx(); d$bad[i] <- 1L - d$bad[i]; rec(d) })
  
  observeEvent(input$save, write.csv(rec(), file.path(INPUT_DIR, "disc_marks.csv"), row.names = FALSE))
  
  output$plot <- renderPlot({
    i <- idx(); im <- imgs[[files[i]]]; d <- rec()
    ras <- im$ras
    if (d$flip[i] == 1L) ras <- ras[nrow(ras):1, ncol(ras):1]
    x1 <- im$x0; x2 <- im$x0 + im$cw; y1 <- im$y0; y2 <- im$y0 + im$ch
    par(mar = c(0, 0, 0, 0))
    plot(NA, xlim = c(x1, x2), ylim = c(y2, y1), xaxs = "i", yaxs = "i", axes = FALSE, asp = 1, xlab = "", ylab = "")
    rasterImage(ras, x1, y2, x2, y1)
    if (!is.na(d$pith_x[i])) points(d$pith_x[i], d$pith_y[i], pch = 4, col = "magenta", cex = 3, lwd = 3)
  })
  
  output$status <- renderText({
    i <- idx(); d <- rec()
    sprintf("%s (%d/%d)\npith: %s, %s\nflip: %d  bad: %d",
            files[i], i, length(files),
            ifelse(is.na(d$pith_x[i]), "-", round(d$pith_x[i])),
            ifelse(is.na(d$pith_y[i]), "-", round(d$pith_y[i])),
            d$flip[i], d$bad[i])
  })
}

shinyApp(ui, server)