message_data = commandArgs(trailingOnly=TRUE)

suppressMessages({
  library(dplyr)
  library(jsonlite)
  library(lmtest)
  library(broom)
  library(randomForest)
  library(caret)
  library(zoo)
})


get_json <- function(data){
  
  suppressWarnings({
    fct_pck <- readRDS(data)
  })
  
  coefs_list <- list()
  infos_list <- list()

  new_pck <- fct_pck 

  for(i in 1:length(fct_pck[[1]])) {
    
    temp <- fct_pck %>% slice(i)
    temp_model <-  temp$models[[1]]
    temp_type <- temp$infos[[1]]
    
    if(temp$type %in% c("ARIMA", "auto.arima")){
      
      residuals = stats::residuals(temp_model) %>% as_tibble()

      if(length(temp_model$coef) == 0){
        coefs_list[[i]] = list('residuals' = residuals, 'Ljung' = NA)
      }else{

        coef = broom::tidy(lmtest::coeftest(temp_model)) %>% 
          as_tibble()

        freq <- timeDate::frequency(residuals[[1]])
        df  <- base::nrow(coef)

        lag <- ifelse(freq > 1, 2 * freq, 10)
        lag <- min(lag, nrow(residuals)/5)
        lag <- max(df + 3, lag)
        
        options(scipen = 20)

        LBtest <- Box.test(zoo::na.approx(residuals), fitdf = df, lag = lag, type = "Ljung")
        LBtest <- as.character(LBtest[["p.value"]])

        coefs_list[[i]] = list('coef' = coef, 'residuals' = residuals, 'Ljung' = LBtest)
      }
      
      infos_list[[i]] = list(
        'arima_order' = temp_type[['arimaorder']],
        'n_steps' = temp_type[['n_steps']],
        'n_steps_original' = temp_type[['n_steps_original']],
        'n_windows' = temp_type[['n_windows']],
        'n_windows_original' = temp_type[['n_windows_original']]
      )

      if ('breakdown' %in% names(temp_type)){
        infos_dataframe = temp_type[['breakdown']][['d2_simp']] %>% as_tibble() 
        infos_dataframe <- infos_dataframe %>% mutate(data_tidy = as.character(data_tidy))
        list_breakdown = list('breakdown' = infos_dataframe)
        infos_list[[i]] = c(infos_list[[i]], list_breakdown)
      }

    }else if (temp$type == "RandomForest"){
      
      features <- randomForest::importance(temp_model)
      coefs_list[[i]] =  features %>% as.data.frame(row.names = rownames(features), col.names = colnames(features))
      infos_list[[i]] = temp_type
      
    }else if(temp$type %in% c("Lasso", "Ridge", "ElasticNet", "LM")){

      infos_list[[i]] = temp$infos[[1]]

      if(temp$type != "LM"){
        
        feats = temp_model$finalModel
        
        coef_imp = stats::coef(temp_model$finalModel, s = temp_model$bestTune$lambda) 
        
        if(!is.null(coef_imp)){
          coef_imp <- coef_imp %>% 
            as.matrix() %>% 
            as.data.frame()
        }
        
        plot = list('y' = feats$beta %>% as.matrix %>% as.data.frame(), 'x' = feats$dev.ratio)
        varimp <- caret::varImp(temp_model, scale = F)
        varimp <- varimp$importance %>% as.data.frame()

        coefs_list[[i]] = list('bestTune' = temp_model$bestTune %>% as.data.frame(), 'plot'= plot, 'coef' = coef_imp, 'varImp' = varimp)
      
      }else{
        coefs_list[[i]] = list('bestTune' = temp$models[[1]]$bestTune %>% as.data.frame())
      }

    }else if(grepl('comb', temp$type, fixed = TRUE)){
      coefs_list[[i]] = character(0)
      infos_list[[i]] = list('method' = temp_type[[1]]$Method, 'models' = temp_type[[1]]$Models)
    }else{
      coefs_list[[i]] = character(0)
      infos_list[[i]] = character(0)
    }

  }

  new_pck$models <- coefs_list
  new_pck$infos <- infos_list

  output_json <- jsonlite::toJSON(new_pck)

  return(output_json)
}

get_json(data = message_data[1])
