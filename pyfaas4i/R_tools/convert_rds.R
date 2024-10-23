message_data = commandArgs(trailingOnly=TRUE)

suppressMessages({
  library(dplyr)
  library(jsonlite)
  library(lmtest)
  library(randomForest)
  library(caret)
  library(zoo)
  library(glmnet)
})

tidy_coef <- function(model) {

  coefs <- lmtest::coeftest(model)[, 1:4, drop = FALSE]
  coefs <- data.frame(term = rownames(coefs),
                     coefs, row.names = NULL)
  names(coefs) <- c("term", "estimate", "std.error", "statistic", "p.value")
  coefs <- dplyr::as_tibble(coefs)

  return(coefs)
}

get_json <- function(data) {

  suppressWarnings({
    fct_pck <- readRDS(data)
  })

  coefs_list <- list()
  infos_list <- list()

  new_pck <- fct_pck
  
  tree_models <- c("RandomForest", "LGBM", "GradientBoosting","XGBoost")

  for (i in 1:length(fct_pck[[1]])) {
    temp <- fct_pck %>% dplyr::slice(i)
    temp_model <- temp$models[[1]]
    temp_type <- temp$infos[[1]]

    if (temp$type %in% c("ARIMA", "auto.arima", "ARIMA_SEASM", "ARIMA_SEASD", "ARIMA_UNIV")) {
      residuals <- stats::residuals(temp_model) %>% as_tibble()

      if (length(temp_model$coef) == 0) {
        coefs_list[[i]] <- list("residuals" = residuals, "Ljung" = NA)
      } else {
        coef <- tidy_coef(temp_model)

        arima_order <- temp_model[["arma"]][c(1, 6, 2, 3, 7, 4, 5)]
        names(arima_order) <- c("p", "d", "q", "P", "D", "Q", "freq")

        freq <- arima_order[["freq"]]

        ## Uma nova literatura sugere que df = p+q
        ## Vide https://robjhyndman.com/hyndsight/ljung_box_df.html
        df <- arima_order[["p"]] + arima_order[["q"]]


        lag <- ifelse(freq > 1, 2 * freq, 10)

        ## Dividimos o numero de linhas por 2,5 considerando que o lag
        ## acima e o cálculo se igualam para uma amostra de 60 pontos
        ## para o caso mensal, que consideramos 36 como o número mínimo de 
        ## pontos para o cálculo de correlação. 
        ## Ex.: Se o lag for 24 e tivermos 60 observações, para o cálculo
        ## da correlação do lag 24 teremos 36 pontos.
        lag <- min(lag, floor(nrow(residuals)/2.5))
        lag <- max(1, lag)

        options(scipen = 20)

        LBtest <- Box.test(zoo::na.approx(residuals), fitdf = df, lag = lag, type = "Ljung")
        LBtest <- as.character(LBtest[["p.value"]])

        coefs_list[[i]] <- list("coef" = coef, "residuals" = residuals, "Ljung" = LBtest)
      }

      get_infos <- temp_type
      get_infos["breakdown"] <- NULL
      names(get_infos)[which(names(get_infos) == "arimaorder")] <- "arima_order"

      infos_list[[i]] <- get_infos

      if ("breakdown" %in% names(temp_type)) {
        infos_dataframe <- temp_type[["breakdown"]][["d2_simp"]] %>% dplyr::as_tibble()
        infos_dataframe <- infos_dataframe %>% dplyr::mutate(data_tidy = as.character(data_tidy))
        list_breakdown <- list("breakdown" = infos_dataframe)
        infos_list[[i]] <- c(infos_list[[i]], list_breakdown)
      }
    } else if (temp$type %in% tree_models) {
      infos_list[[i]] <- temp_type
      if (!is.null(temp_model)) {
        features <- randomForest::importance(temp_model)
        coefs_list[[i]] <- features %>% as.data.frame(row.names = rownames(features), col.names = colnames(features))
      } else {
        coefs_list[[i]] <- temp_type[["importance"]]
        # Then we drop importance from infos_list
        infos_list[[i]] <- infos_list[[i]][names(infos_list[[i]]) != "importance"]
      }
      
    } else if (temp$type %in% c("Lasso", "Ridge", "ElasticNet", "LM")) {
      infos_list[[i]] <- temp$infos[[1]]

      is_v5 <- FALSE
      if (! "finalModel" %in% names(temp_model)) {
        
        is_v5 <- TRUE
        
        temp_model[["finalModel"]] <- temp_model
        
        ## Defining alpha
        if (temp$type == "ElasticNet") {
          alpha <- temp_model[["call"]][["alpha"]]
        } else if (temp$type == "Lasso") {
          alpha <- 1
        } else if (temp$type %in% c("Ridge", "LM")) {
          alpha <- 0
        }
        
        bestTune <- data.frame(alpha = alpha,
                               lambda = temp_model[["lambda"]])
        temp_model[["bestTune"]] <- bestTune
        temp$models[[1]][["bestTune"]] <- bestTune
      }

      if (temp$type != "LM") {
        feats <- temp_model$finalModel

        coef_imp <- stats::coef(temp_model$finalModel, s = temp_model$bestTune$lambda)

        if (!is.null(coef_imp)) {
          coef_imp <- coef_imp %>%
            as.matrix() %>%
            as.data.frame()
        }

        plot <- list("y" = feats$beta %>% as.matrix() %>% as.data.frame(), "x" = feats$dev.ratio)
        
        if (is_v5) {
          varimp <- caret::varImp(temp_model, scale = F, lambda = temp_model$bestTune$lambda) %>% 
            as.data.frame()
        } else {
          varimp <- caret::varImp(temp_model, scale = F)
          varimp <- varimp$importance %>% as.data.frame()
        }

        coefs_list[[i]] <- list("bestTune" = temp_model$bestTune %>% as.data.frame(), "plot" = plot, "coef" = coef_imp, "varImp" = varimp)
      } else {
        coefs_list[[i]] <- list("bestTune" = temp$models[[1]]$bestTune %>% as.data.frame())
      }
    } else if (grepl("comb", temp$type, fixed = TRUE)) {
      coefs_list[[i]] <- character(0)
      infos_list[[i]] <- list(
        "method" = temp_type[[1]]$Method, "models" = temp_type[[1]]$Models
      )

      keep_infos <- c(
        "n_steps", "n_windows", "n_steps_original", "n_windows_original",
        "window_update", "freq_num", "freq_date", "version",
        "out_exante", "out_expost"
      )

      for (info in keep_infos) {
        if (info %in% names(temp_type)) {
          new_item_list <- list(temp_type[[info]])
          names(new_item_list) <- get("info")
          infos_list[[i]] <- c(infos_list[[i]], new_item_list)
        }
      }
    } else {
      coefs_list[[i]] <- character(0)
      infos_list[[i]] <- temp_type
    }
  }

  new_pck$models <- coefs_list
  new_pck$infos <- infos_list

  output_json <- jsonlite::toJSON(new_pck)

  return(output_json)
}

get_json(data = message_data[1])
