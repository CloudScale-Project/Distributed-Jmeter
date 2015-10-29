###########################
# load required libraries #
###########################
library(ggplot2)
library(scales)

#################################
# read csv files to data frames #
#################################
df<-read.csv(f,header=TRUE)
slo_df<-read.csv(slo_f, header=TRUE)

if(file.exists(as_f))
{
    as_df<-read.csv(as_f, header=TRUE)
}

mdf<-read.csv(m_f, header=TRUE, row.names=NULL)
slo_df_non_agg <- read.csv(slo_f_non_aggregated, header=TRUE)
#slo_agg_1second_df <- read.csv(slo_agg_1second, header=TRUE)
slo_agg_5seconds_df <- read.csv(slo_agg_5seconds, header=TRUE)
slo_agg_10seconds_df <- read.csv(slo_agg_10seconds, header=TRUE)
ec2_cpu_df <- read.csv(ec2_file, header=TRUE)
rds_cpu_df <- read.csv(rds_cpu_file, header=TRUE)

start_date <- min(df$date)
end_date <- max(df$date)
####################
# define functions #
####################
get_vline <- function(df)
{
    index <- which(df$when_violates != "" & !is.na(df$when_violates))
    return(as.numeric(df[index+1, 'date']))
}

normalized_response_time <- function(df, scale=1)
{
	if( nrow(df) == 0)
	{
		df[1, 'response_time_normalized'] <- 0
		df <- df[-c(1), ]
		return(df)
	}
	my_df <- df
	for(i in 1:nrow(df))
	{
		normalized_value <- scale/SLO[1, df[i, 'url']]
		my_df[i, 'response_time_normalized'] <- df[i, 'response_time']*normalized_value
	}

	return(my_df)
}

cut_scenario <- function(df, duration)
{
	steps <- (scenario_duration_in_min*60)/duration
    if (nrow(df) > steps+1)
    {

        c <- seq.int(nrow(df) + (steps - nrow(df)) + 2, nrow(df), 1)
        return(df[-c,])
    }
    return(df)
}

#when_violates <- function(df, start=2)
#{
#	stop <- FALSE
#	for(i in start:nrow(df))
#	{
#	    f <- as.numeric(df[i, 'percent_slo'])
#		if( !is.na(f) & f > 10 & !stop)
#		{
#		    print(i)
#			df[i-1, 'when_violates'] <- sprintf("req. = %s (%s) / VU = (%s)", round(df[i-1, "theorethical_requests"]), df[i-1, 'num_all_requests'], round(as.numeric(df[i-1, 'vus'])))
#			stop <- TRUE
#		}
#		else
#		{
#			df[i, 'when_violates'] <- ""
#		}
#	}
#
#	return(df)
#}

transform_date <- function(df, field="date")
{
	df[,field] <- as.POSIXct(df[,field]/1000, origin='1970-01-01')
	return(df)
}

order_by_date <- function(df, field="date"){
	my_df<-df[order(df[,field]),]
	return(my_df)
}


#create_vus <- function(df)
#{
#	df<-order_by_date(df)
#	threads_per_minute <- num_threads/ (nrow(df)-1)
#	for(i in 1:nrow(df)){
#		df[i, "vus"] <- round((i-1)*threads_per_minute)
#	}
#	return(df)
#}

add_scale_x <- function(gg, df){
	my_breaks <- seq.int(0, scenario_duration_in_min*60, 60)
	return(gg + theme(axis.text.x = element_text(angle = 90, hjust = 1)) + scale_x_continuous(breaks=my_breaks, labels=format(as.POSIXct(my_breaks, origin="1970-01-01 00:00:00"), format="%H:%M:%S")))
}


date2scenario_time <- function(df, field="date")
{
	min_d <- as.numeric(min(df[,field]))
	df$scenario_date <- as.POSIXct(as.numeric(df[,field])-min_d, origin="1970-01-01 00:00:00")
	return(df)
}

date2scenario_time2 <- function(df, field="date")
{
	min_d <- as.numeric(min(df[,field]))
	df$scenario_date <- as.POSIXct(abs(as.numeric(df[,field]-start_date))*60, origin="1970-01-01 00:00:00")
	return(df)
}


#add_requests_per_second <- function(df, duration){
#	my_df <- df
#
#	scenario_duration_in_sec <- scenario_duration*60
#
#	requests_per_second <- (num_threads/7)
#	requests_per_scenario <- requests_per_second * scenario_duration_in_sec
#	requests_per_duration <- requests_per_scenario/(scenario_duration_in_sec/duration)
#	inc <- requests_per_duration/nrow(my_df)
#
#    my_df[1, "drek"] <- 0
#	for(i in 2:nrow(my_df)){
#		my_df[i, "drek"] <- as.numeric((i-1)*inc)
#	}
#	return(my_df)
#}
#
#add_theorethical_requests <- function(df, duration)
#{
#	scenario_duration_in_sec <- scenario_duration*60
#	requests_per_second <- (num_threads/7)
#	num_intervals <- scenario_duration_in_sec/duration
#
#	requests_per_scenario <- requests_per_second * scenario_duration_in_sec
#	requests_per_duration <- requests_per_scenario/num_intervals
#
#	requests_per_interval <- requests_per_duration/num_intervals
#	df[1, "num_requests_theory"] <- 0
#	for(i in 1:(nrow(df)-1))
#	{
#		df[i+1, "num_requests_theory"] <- (((i-1) * requests_per_interval) + (i * requests_per_interval))/2
#	}
#
#	return(df)
#}

insertrow <- function(existingdf, newrow, r)
{
	existingdf[seq(r+1,nrow(existingdf)+1),] <- existingdf[seq(r,nrow(existingdf)),]
	existingdf[r,] <- newrow
	existingdf
}

multiplot <- function(..., plotlist=NULL, file, cols=1, layout=NULL) {
  require(grid)

  # Make a list from the ... arguments and plotlist
  plots <- c(list(...), plotlist)

  numPlots = length(plots)

  # If layout is NULL, then use 'cols' to determine layout
  if (is.null(layout)) {
    # Make the panel
    # ncol: Number of columns of plots
    # nrow: Number of rows needed, calculated from # of cols
    layout <- matrix(seq(1, cols * ceiling(numPlots/cols)),
                    ncol = cols, nrow = ceiling(numPlots/cols))
  }

 if (numPlots==1) {
    print(plots[[1]])

  } else {
    # Set up the page
    grid.newpage()
    pushViewport(viewport(layout = grid.layout(nrow(layout), ncol(layout))))

    # Make each plot, in the correct location
    for (i in 1:numPlots) {
      # Get the i,j matrix positions of the regions that contain this subplot
      matchidx <- as.data.frame(which(layout == i, arr.ind = TRUE))

      print(plots[[i]], vp = viewport(layout.pos.row = matchidx$row,
                                      layout.pos.col = matchidx$col))
    }
  }
}

########################################
# transform timestamps to date objects #
########################################
slo_df <- transform_date(slo_df)
mdf <- transform_date(mdf)
df <- transform_date(df)
slo_df_non_agg <- transform_date(slo_df_non_agg)
#slo_agg_1second_df <- transform_date(slo_agg_1second_df)
slo_agg_5seconds_df <- transform_date(slo_agg_5seconds_df)
slo_agg_10seconds_df <- transform_date(slo_agg_10seconds_df)

############################
# order data frame by date #
############################
slo_df<-order_by_date(slo_df)
mdf <- order_by_date(mdf)
df <- order_by_date(df)
slo_df_non_agg <- order_by_date(slo_df_non_agg)
#slo_agg_1second_df <- order_by_date(slo_agg_1second_df)
slo_agg_5seconds_df <- order_by_date(slo_agg_5seconds_df)
slo_agg_10seconds_df <- order_by_date(slo_agg_10seconds_df)
rds_cpu_df <- order_by_date(rds_cpu_df, "timestamp")

################
# Cut scenario #
################
slo_df <- cut_scenario(slo_df, 60)

#slo_agg_1second_df <- cut_scenario(slo_agg_1second_df, 1)

slo_agg_5seconds_df <- cut_scenario(slo_agg_5seconds_df, 5)

slo_agg_10seconds_df <- cut_scenario(slo_agg_10seconds_df, 10)


##################
# transform data #
##################
slo_df_non_agg$response_code <- factor(slo_df_non_agg$response_code)

scenario_duration <- c(max(slo_df$date) - min(slo_df$date))

num_ec2_instances <- length(levels(ec2_cpu_df$instance_id))

#slo_df <- create_vus(slo_df)
#slo_agg_1second_df <- create_vus(slo_agg_1second_df)
#slo_agg_5seconds_df <- create_vus(slo_agg_5seconds_df)
#slo_agg_10seconds_df <- create_vus(slo_agg_10seconds_df)

specify_decimal <- function(x, k) format(round(x, k), nsmall=k)

# change time to match scenario time
#slo_df <- add_requests_per_second(slo_df, 60)
#slo_agg_1second_df <- add_requests_per_second(slo_agg_1second_df, 1)
#slo_agg_5seconds_df <- add_requests_per_second(slo_agg_5seconds_df, 5)
#slo_agg_10seconds_df <- add_requests_per_second(slo_agg_10seconds_df, 10)

ec2_cpu_avg <- aggregate(average ~ timestamp, ec2_cpu_df, mean)
ec2_cpu_avg$timestamp <- seq.int(60, nrow(ec2_cpu_avg)*60, 60)
ec2_cpu_avg <- insertrow(ec2_cpu_avg, c(0,0), 1)

rds_cpu_df <- insertrow(rds_cpu_df, c(as.character(rds_cpu_df[1,"instance_id"]),0,0), 1)
rds_cpu_df$timestamp <- seq.int(0, (nrow(rds_cpu_df)-1)*60, 60)

#############################################
# calculate theorethical number of requests #
#############################################

#slo_df <- add_theorethical_requests(slo_df, 60)
#slo_agg_1second_df <- add_theorethical_requests(slo_agg_1second_df, 1)
#slo_agg_5seconds_df <- add_theorethical_requests(slo_agg_5seconds_df, 5)
#slo_agg_10seconds_df <- add_theorethical_requests(slo_agg_10seconds_df, 10)

##########################################
# calculate percentage of slo violations #
##########################################

#slo_df$num_threads <- ifelse(slo_df$num > 0, specify_decimal((100*slo_df$num)/slo_df$num_all_requests, 2), "")
#slo_agg_5seconds_df$num_threads <- ifelse(slo_agg_5seconds_df$num > 0, specify_decimal((100*slo_agg_5seconds_df$num)/slo_agg_5seconds_df$num_all_requests, 2), "")
#slo_agg_10seconds_df$num_threads <- ifelse(slo_agg_10seconds_df$num > 0, specify_decimal((100*slo_agg_10seconds_df$num)/slo_agg_10seconds_df$num_all_requests, 2), "")

##################################
# add text when starts violating #
##################################

#slo_df <- when_violates(slo_df)
#slo_agg_5seconds_df <- when_violates(slo_agg_5seconds_df, start=20)
#slo_agg_10seconds_df <- when_violates(slo_agg_10seconds_df, start=10)

####################################
# transform times to scenario time #
####################################
slo_df <- date2scenario_time(slo_df)

#slo_agg_1second_df <- date2scenario_time(slo_agg_1second_df)

slo_agg_5seconds_df <- date2scenario_time(slo_agg_5seconds_df)

slo_agg_10seconds_df <-date2scenario_time(slo_agg_10seconds_df)

df <- date2scenario_time(df)

slo_df_non_agg <- date2scenario_time(slo_df_non_agg)

mdf <- date2scenario_time(mdf)

# slo_df_non_agg <- normalized_response_time(slo_df_non_agg)

#################
# define graphs #
#################
common_1minute_gg <- ggplot(slo_df, aes(x=as.numeric(scenario_date), y=num_all_requests)) +
	geom_line() +
	geom_vline(xintercept=get_vline(slo_df), colour="red") +
	geom_line(data=slo_df, aes(x=as.numeric(scenario_date), y=requests_per_interval), colour="blue") +
	geom_bar(stat="identity", data=slo_df, aes(x=as.numeric(scenario_date), y=num)) +
	geom_text(data=slo_df, size=5, vjust=-1.5, aes(label=when_violates))

common_5seconds_gg <- ggplot(slo_agg_5seconds_df, aes(x=as.numeric(scenario_date), y=num_all_requests)) +
	geom_line() +
	geom_vline(xintercept=get_vline(slo_agg_5seconds_df), colour="red") +
	geom_line(data=slo_agg_5seconds_df, aes(x=as.numeric(scenario_date), y=requests_per_interval), colour="blue") +
	geom_bar(stat="identity", data=slo_agg_5seconds_df, aes(x=as.numeric(scenario_date), y=num)) +
	geom_text(data=slo_agg_5seconds_df, size=5, vjust=-1.5, aes(label=when_violates))

common_10seconds_gg <- ggplot(slo_agg_10seconds_df, aes(x=as.numeric(scenario_date), y=num_all_requests)) +
	geom_line() +
	geom_vline(xintercept=get_vline(slo_agg_10seconds_df), colour="red") +
	geom_line(data=slo_agg_10seconds_df, aes(x=as.numeric(scenario_date), y=requests_per_interval), colour="blue") +
	geom_bar(stat="identity", data=slo_agg_10seconds_df, aes(x=as.numeric(scenario_date), y=num)) +
	geom_text(data=slo_agg_10seconds_df, size=5, vjust=-1.5, aes(label=when_violates))

scenario_gg <- ggplot(slo_df, aes(x=as.numeric(scenario_date), y=num_all_requests)) +
	geom_line(stat="identity") +
	ylab(label="no requests") +
	xlab(label="Time (minute)")

#slo_df$linear <- seq(0, max(slo_df$vus), length.out=nrow(slo_df))
slo_gg2 <- ggplot(slo_df, aes(x=as.numeric(scenario_date), y=num)) +
	geom_bar(stat="identity") +
	ylab(label="# SLO violations") +
	xlab(label="Time (minute)")

slo_non_agg_gg <- ggplot(slo_df_non_agg, aes(x=as.numeric(scenario_date), y=response_time, colour=response_code)) +
	geom_point() +
	ylab(label="response time") +
	xlab(label="Time (minute)")

slo_non_agg_gg_urls <- ggplot(slo_df_non_agg, aes(x=as.numeric(scenario_date), y=response_time, colour=url)) +
	geom_point() +
	ylab(label="response time") +
	xlab(label="Time (minute)")

# slo_non_agg_gg_urls_normalized <- ggplot(slo_df_non_agg, aes(x=as.numeric(scenario_date), y=response_time_normalized, colour=url)) +
#	geom_point() +
#	ylab(label="response time") +
#	xlab(label="time") +
#	ggtitle("slo violations by url - normalized")


# slo_non_agg_gg_normalized <- ggplot(slo_df_non_agg, aes(x=as.numeric(scenario_date), y=response_time_normalized, colour=response_code)) +
#	geom_point() +
#	ylab(label="response time") +
#	xlab(label="time") +
#	ggtitle("slo_violations by response code - normalized")

gg <- ggplot(df, aes(x=as.numeric(scenario_date), y=response_time, colour=url)) +
	geom_point() +
	xlab(label="Time (minute)")

#gg2 <- ggplot(slo_df, aes(x=vus, y=num_all_requests)) +
#	geom_point(stat="identity") +
#	scale_x_continuous(breaks=seq(0, max(slo_df$vus), num_threads/10))
#	#geom_line(data=slo_df, aes(x=as.numeric(scenario_date), y=drek)) +

#slo_agg_1second_gg <- ggplot(slo_agg_1second_df, aes(x=as.numeric(scenario_date), y=num_all_requests)) +
#	geom_line(stat="identity") +
#	ylab(label="no requests") +
#	xlab(label="Time (minute)")

slo_agg_5seconds_gg <- ggplot(slo_agg_5seconds_df, aes(x=as.numeric(scenario_date), y=num_all_requests)) +
	geom_line(stat="identity") +
	ylab(label="no requests") +
	xlab(label="Time (minute)")

slo_agg_10seconds_gg <- ggplot(slo_agg_10seconds_df, aes(x=as.numeric(scenario_date), y=num_all_requests)) +
	geom_line(stat="identity") +
	ylab(label="no requests") +
	xlab(label="Time (minute)")

ec2_cpu_avg$linear <- seq(0, 100, length.out=nrow(ec2_cpu_avg))
ec2_cpu_gg <- ggplot(ec2_cpu_avg, aes(x=as.numeric(timestamp), y=average)) +
	geom_line() +
	geom_point() +
	ylab("CPU utilisation") +
	xlab("Time (minute)") +
	geom_text(vjust=2, aes(label=round(as.numeric(average),digits=2)))+
    geom_line(aes(y=linear, colour='red'))

rds_cpu_gg <- ggplot(rds_cpu_df, aes(x=as.numeric(timestamp), y=as.double(average))) +
	geom_line() +
	geom_point() +
	ylab("CPU utilisation") +
	xlab("Time (minute)") +
	geom_text(vjust=2, aes(label=round(as.numeric(average), digits=2)))

################################
# add vm provisioning to graph #
################################
if(nrow(mdf) > 0)
{
	rate <- num_threads/scenario_duration_in_min
	mdf$vus<-round((as.numeric(mdf$scenario_date)/60)*rate)
	
    over_provisioning_gg <- ggplot(slo_df, aes(x=as.numeric(scenario_date), y=vus)) +
		geom_line() +
		geom_line(data=mdf, aes(x=as.numeric(scenario_date), y=y*50, colour=instance_id), size=2) +
		geom_step(direction="vh", data=mdf, aes(x=as.numeric(scenario_date), y=vus)) +
		geom_text(data=mdf, aes(label=vus))

	
	slo_gg2 <- slo_gg2 + geom_line(data=mdf, aes(x=as.numeric(scenario_date),y=y*50, colour=instance_id), size=2)

	slo_non_agg_gg <- slo_non_agg_gg + geom_line(data=mdf, aes(x=as.numeric(scenario_date),y=y*1000, colour=instance_id), size=2)

	gg <- gg + geom_line(data=mdf, aes(x=as.numeric(scenario_date),y=y*1000, colour=instance_id), size=2)
}

##################
# scale x-origin #
##################

common_1minute_gg <- add_scale_x(common_1minute_gg, slo_df)

common_5seconds_gg <- add_scale_x(common_5seconds_gg, slo_agg_5seconds_df)

common_10seconds_gg <- add_scale_x(common_10seconds_gg, slo_agg_10seconds_df)

scenario_gg <- add_scale_x(scenario_gg, slo_df)

slo_gg2 <- add_scale_x(slo_gg2, slo_df)

slo_non_agg_gg <- add_scale_x(slo_non_agg_gg, slo_df_non_agg)

slo_non_agg_gg_urls <- add_scale_x(slo_non_agg_gg_urls, slo_df_non_agg)

#slo_non_agg_gg_urls_normalized <- add_scale_x(slo_non_agg_gg_urls_normalized, slo_df_non_agg)

#slo_non_agg_gg_normalized <- add_scale_x(slo_non_agg_gg_normalized, slo_df_non_agg)

gg <- add_scale_x(gg, df)

#slo_agg_1second_gg <- add_scale_x(slo_agg_1second_gg, slo_agg_1second_df)

slo_agg_5seconds_gg <- add_scale_x(slo_agg_5seconds_gg,slo_agg_5seconds_df)

slo_agg_10seconds_gg <- add_scale_x(slo_agg_10seconds_gg,slo_agg_10seconds_df)

ec2_cpu_gg <- add_scale_x(ec2_cpu_gg, ec_cpu_avg)

ec2_cpu_gg <- ec2_cpu_gg + scale_y_continuous(breaks=seq.int(0, 100, 10))

rds_cpu_gg <- add_scale_x(rds_cpu_gg, rds_cpu_df)

rds_cpu_gg <- rds_cpu_gg + scale_y_continuous(breaks=seq.int(0, 100, 10))

max_date <- max(df$date)

if(exists("over_provisioning_gg"))
{
	over_provisioning_gg <- add_scale_x(over_provisioning_gg, mdf)
}

########################
# add layers to graphs #
########################
if(exists("over_provisioning_gg"))
{
	over_provisioning_gg <- over_provisioning_gg + xlab(label='Time (minute)') + ylab(label='VUS') + ggtitle('VM provisioning')
}
common_1minute_gg <- common_1minute_gg + xlab(label='Time (minute)') + ylab(label='requests') + ggtitle("SLO violations - 1 minute")

common_5seconds_gg <- common_5seconds_gg + xlab(label='Time (minute)') + ylab(label='requests') + ggtitle("SLO violations - 5 second")

common_10seconds_gg <- common_10seconds_gg + xlab(label='Time (minute)') + ylab(label='requests')  + ggtitle("SLO violations - 10 seconds")

scenario_gg <- scenario_gg + geom_line(data=mdf, aes(x=date,y=y*1000, colour=instance_id), size=2)  + ggtitle("Requests aggregated by 1 minute")

#slo_agg_1second_gg <- slo_agg_1second_gg + geom_line(data=mdf, aes(x=date,y=y*1000, colour=instance_id), size=2)  + ggtitle("Requests aggregated by 1 second")

slo_agg_5seconds_gg <- slo_agg_5seconds_gg + geom_line(data=mdf, aes(x=date,y=y*1000, colour=instance_id), size=2)  + ggtitle("Requests aggregated by 5 seconds")

slo_agg_10seconds_gg <- slo_agg_10seconds_gg + geom_line(data=mdf, aes(x=date,y=y*1000, colour=instance_id), size=2)  + ggtitle("Requests aggregated by 10 seconds")

my_gg <- slo_agg_10seconds_gg + geom_line(data=slo_df, aes(x=as.numeric(scenario_date), y=vus))

# gg2 <- gg2 + xlab(label='virtual users') + ylab(label='requests')

slo_non_agg_gg_urls <- slo_non_agg_gg_urls + xlab(label='Time (minute)') + ylab(label='response time') + ggtitle("SLO violations by url")

ec2_cpu_gg <- ec2_cpu_gg + ggtitle(paste("Average CPU utilisation of", num_ec2_instances, "instances - by minute", sep=" "))

rds_cpu_gg <- rds_cpu_gg + ggtitle(paste("Average CPU utilisation of RDS - by minute"))

slo_gg2 <- slo_gg2  + ggtitle("SLO violations - 1 minute")

slo_non_agg_gg <- slo_non_agg_gg  + ggtitle("SLO violations by response code")

gg <- gg + xlab(label='Time (minute)') + ylab(label='response time') # + ggtitle("All responses")

min_y <- ifelse(nrow(mdf) > 0, min(mdf$y), 0)
slo_gg2 <- slo_gg2 +
	geom_text(data=slo_df, size=3, vjust=-0.5, aes(label=percent_slo))

if(nrow(mdf) == 0)
{
	slo_gg2 <- slo_gg2 + ylim(min_y * 10, max(slo_df$num) + 50)
}

#######################
# save graphs to file #
#######################
pdf(paste(output_dir, "/ec2_cpu.pdf", sep=""), width=20)
plot(ec2_cpu_gg)
dev.off()

pdf(paste(output_dir , "/rds_cpu.pdf", sep=""), width=20)
plot(rds_cpu_gg)
dev.off()

pdf(paste(output_dir , "/slo_violations.pdf", sep=""), width=20)
plot(slo_gg2)
dev.off()

pdf(paste(output_dir, "/slo_response_code.pdf", sep=""), width=20)
plot(slo_non_agg_gg)
dev.off()

pdf(paste(output_dir, "/slo_urls.pdf", sep=""), width=20)
plot(slo_non_agg_gg_urls)
dev.off()

pdf(paste(output_dir, "/response.pdf", sep=""), width=20)
plot(gg)
dev.off()

pdf(paste(output_dir, "/1minute.pdf", sep=""), width=20)
plot(common_1minute_gg)
dev.off()

pdf(paste(output_dir, "/5seconds.pdf", sep=""), width=20)
plot(common_5seconds_gg)
dev.off()

pdf(paste(output_dir, "/10seconds.pdf", sep=""), width=20)
plot(common_10seconds_gg)
dev.off()

if(exists("over_provisioning_gg"))
{
	pdf(paste(output_dir, "/vm_provisioning.pdf", sep=""), width=20)
	plot(over_provisioning_gg)
	dev.off()
}